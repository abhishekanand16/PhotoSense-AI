#!/usr/bin/env python3
"""
PhotoSense-AI CLI entrypoint.

Offline photo organization system with facial recognition and clustering.
"""

import click
import logging
import sys
from pathlib import Path

from src.db.database import Database
from src.scanner.scan_images import scan_directory
from src.scanner.metadata import extract_metadata
from src.face.detect import FaceDetector
from src.face.encode import FaceEncoder
from src.face.cluster import FaceClusterer
from src.search.search import ImageSearcher

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


@click.group()
def cli():
    """PhotoSense-AI: Offline photo organization with facial recognition."""
    pass


@cli.command()
@click.option('--input', '-i', required=True, help='Directory to scan for images')
@click.option('--db', default='photosense.db', help='Path to database file')
@click.option('--recursive/--no-recursive', default=True, help='Scan subdirectories recursively')
def scan(input: str, db: str, recursive: bool):
    """
    Scan directory for images and extract metadata.

    This command:
    1. Recursively finds all image files in the specified directory
    2. Extracts EXIF metadata (date taken, camera model, dimensions)
    3. Stores image records in the database
    """
    logger.info(f"Starting scan of directory: {input}")
    logger.info(f"Using database: {db}")

    try:
        # Scan for images
        logger.info("Scanning for image files...")
        image_files = scan_directory(input, recursive=recursive)
        logger.info(f"Found {len(image_files)} image files")

        if not image_files:
            logger.warning("No image files found in the specified directory")
            return

        # Initialize database
        db_manager = Database(db)

        # Process each image
        processed = 0
        skipped = 0
        errors = 0

        for image_path in image_files:
            try:
                # Extract metadata
                metadata = extract_metadata(image_path)

                # Add to database
                image_id = db_manager.add_image(
                    file_path=image_path,
                    date_taken=metadata.get('date_taken'),
                    camera_model=metadata.get('camera_model'),
                    width=metadata.get('width'),
                    height=metadata.get('height'),
                    file_size=metadata.get('file_size'),
                )

                if image_id:
                    processed += 1
                    if processed % 100 == 0:
                        logger.info(f"Processed {processed} images...")
                else:
                    skipped += 1  # Already exists in DB

            except Exception as e:
                errors += 1
                logger.error(f"Error processing {image_path}: {e}")

        db_manager.close()

        logger.info(f"Scan complete: {processed} processed, {skipped} skipped, {errors} errors")

    except Exception as e:
        logger.error(f"Scan failed: {e}")
        sys.exit(1)


@cli.command()
@click.option('--db', default='photosense.db', help='Path to database file')
@click.option('--output', '-o', default='data/faces', help='Directory to save cropped faces')
@click.option('--min-confidence', default=0.9, help='Minimum confidence threshold for face detection')
@click.option('--skip-existing', is_flag=True, help='Skip images that already have detected faces')
def detect(db: str, output: str, min_confidence: float, skip_existing: bool):
    """
    Detect faces in scanned images.

    This command:
    1. Loads all images from the database
    2. Detects faces in each image using MTCNN
    3. Crops and saves detected faces
    4. Stores face records in the database
    """
    logger.info(f"Starting face detection")
    logger.info(f"Using database: {db}")
    logger.info(f"Output directory: {output}")

    try:
        # Initialize database
        db_manager = Database(db)

        # Get all images
        images = db_manager.get_all_images()
        logger.info(f"Found {len(images)} images in database")

        if not images:
            logger.warning("No images found in database. Run 'scan' command first.")
            return

        # Initialize face detector
        detector = FaceDetector()

        # Create output directory
        output_path = Path(output)
        output_path.mkdir(parents=True, exist_ok=True)

        # Process each image
        processed = 0
        faces_detected = 0
        errors = 0

        for image_record in images:
            image_path = image_record['file_path']
            image_id = image_record['id']

            # Check if we should skip this image
            if skip_existing:
                # Check if faces already exist for this image
                cursor = db_manager.conn.cursor()
                cursor.execute("SELECT COUNT(*) FROM faces WHERE image_id = ?", (image_id,))
                existing_count = cursor.fetchone()[0]
                if existing_count > 0:
                    logger.debug(f"Skipping {image_path} (already has {existing_count} faces)")
                    continue

            try:
                # Check if image file exists
                if not Path(image_path).exists():
                    logger.warning(f"Image file not found: {image_path}")
                    continue

                # Detect and crop faces
                detections = detector.process_image(
                    image_path,
                    str(output_path),
                    min_confidence=min_confidence
                )

                # Store face records in database
                for detection in detections:
                    face_id = db_manager.add_face(
                        image_id=image_id,
                        face_path=detection['face_path'],
                        bbox_x=detection['bbox'][0],
                        bbox_y=detection['bbox'][1],
                        bbox_width=detection['bbox'][2],
                        bbox_height=detection['bbox'][3],
                        confidence=detection['confidence'],
                    )
                    faces_detected += 1

                processed += 1
                if processed % 10 == 0:
                    logger.info(f"Processed {processed} images, detected {faces_detected} faces...")

            except Exception as e:
                errors += 1
                logger.error(f"Error processing {image_path}: {e}")

        db_manager.close()

        logger.info(
            f"Face detection complete: {processed} images processed, "
            f"{faces_detected} faces detected, {errors} errors"
        )

    except Exception as e:
        logger.error(f"Face detection failed: {e}")
        sys.exit(1)


@cli.command()
@click.option('--db', default='photosense.db', help='Path to database file')
@click.option('--output', '-o', default='data/embeddings', help='Directory to save embeddings')
@click.option('--skip-existing', is_flag=True, help='Skip faces that already have embeddings')
def encode(db: str, output: str, skip_existing: bool):
    """
    Generate face embeddings for detected faces.

    This command:
    1. Loads all detected faces from the database
    2. Generates facial embeddings using FaceNet
    3. Saves embeddings to disk
    4. Updates face records with embedding paths
    """
    logger.info("Starting face encoding")
    logger.info(f"Using database: {db}")
    logger.info(f"Output directory: {output}")

    try:
        # Initialize database
        db_manager = Database(db)

        # Get faces that need encoding
        if skip_existing:
            faces = db_manager.get_faces_without_embeddings()
        else:
            faces = db_manager.get_all_faces()

        logger.info(f"Found {len(faces)} faces to encode")

        if not faces:
            logger.warning("No faces found in database. Run 'detect' command first.")
            return

        # Initialize face encoder
        encoder = FaceEncoder()

        # Create output directory
        output_path = Path(output)
        output_path.mkdir(parents=True, exist_ok=True)

        # Process each face
        processed = 0
        errors = 0

        for face_record in faces:
            face_id = face_record['id']
            face_image_path = face_record['face_path']

            # Check if face image exists
            if not face_image_path or not Path(face_image_path).exists():
                logger.warning(f"Face image not found: {face_image_path}")
                errors += 1
                continue

            try:
                # Generate and save embedding
                embedding_path = encoder.process_face(
                    face_image_path,
                    str(output_path)
                )

                if embedding_path:
                    # Update face record with embedding path
                    cursor = db_manager.conn.cursor()
                    cursor.execute(
                        "UPDATE faces SET embedding_path = ? WHERE id = ?",
                        (embedding_path, face_id)
                    )
                    db_manager.conn.commit()

                    processed += 1
                    if processed % 50 == 0:
                        logger.info(f"Processed {processed} faces...")
                else:
                    errors += 1
                    logger.warning(f"Failed to encode face {face_id}")

            except Exception as e:
                errors += 1
                logger.error(f"Error processing face {face_id}: {e}")

        db_manager.close()

        logger.info(
            f"Face encoding complete: {processed} faces encoded, {errors} errors"
        )

    except Exception as e:
        logger.error(f"Face encoding failed: {e}")
        sys.exit(1)


@cli.command()
@click.option('--db', default='photosense.db', help='Path to database file')
@click.option('--eps', default=0.5, help='DBSCAN eps parameter (maximum distance in cluster)')
@click.option('--min-samples', default=3, help='DBSCAN min_samples parameter (minimum faces per cluster)')
@click.option('--metric', default='cosine', type=click.Choice(['cosine', 'euclidean']), help='Distance metric for clustering')
def cluster(db: str, eps: float, min_samples: int, metric: str):
    """
    Cluster faces using unsupervised learning (DBSCAN).

    This command:
    1. Loads all face embeddings from the database
    2. Clusters faces using DBSCAN
    3. Creates person records for each cluster
    4. Links faces to their assigned clusters
    """
    logger.info("Starting face clustering")
    logger.info(f"Using database: {db}")
    logger.info(f"Parameters: eps={eps}, min_samples={min_samples}, metric={metric}")

    try:
        # Initialize database
        db_manager = Database(db)

        # Get all faces with embeddings
        faces = db_manager.get_faces_without_person()
        logger.info(f"Found {len(faces)} faces to cluster")

        if not faces:
            logger.warning("No faces with embeddings found. Run 'encode' command first.")
            return

        # Initialize clusterer
        clusterer = FaceClusterer(eps=eps, min_samples=min_samples)

        # Load embeddings
        logger.info("Loading face embeddings...")
        embeddings, face_ids = clusterer.load_embeddings(faces)

        if len(embeddings) == 0:
            logger.error("No embeddings could be loaded")
            return

        # Perform clustering
        logger.info("Clustering faces...")
        labels = clusterer.cluster(embeddings, metric=metric)

        # Get cluster statistics
        stats = clusterer.get_cluster_stats(labels)
        logger.info(f"Clustering results: {stats['n_clusters']} clusters, {stats['n_noise']} noise points")

        # Create person records and assign faces
        cluster_to_person_id = {}  # Map cluster_id -> person_id

        # Process each cluster
        unique_clusters = set(labels)
        for cluster_id in unique_clusters:
            if cluster_id == -1:
                # Noise points - don't create person records
                continue

            # Create person record for this cluster
            person_id = db_manager.add_person(cluster_id=cluster_id, name=None)
            cluster_to_person_id[cluster_id] = person_id
            logger.debug(f"Created person record {person_id} for cluster {cluster_id}")

        # Assign faces to clusters
        assigned = 0
        for idx, face_id in enumerate(face_ids):
            cluster_id = labels[idx]

            if cluster_id == -1:
                # Noise point - leave person_id as NULL
                continue

            person_id = cluster_to_person_id.get(cluster_id)
            if person_id:
                db_manager.update_face_person(face_id, person_id)
                assigned += 1

        db_manager.close()

        logger.info(
            f"Clustering complete: {stats['n_clusters']} clusters created, "
            f"{assigned} faces assigned, {stats['n_noise']} noise points"
        )

    except Exception as e:
        logger.error(f"Face clustering failed: {e}")
        sys.exit(1)


@cli.command()
@click.option('--db', default='photosense.db', help='Path to database file')
@click.option('--person', help='Search by person name')
@click.option('--date', help='Search by exact date (YYYY-MM-DD)')
@click.option('--start-date', help='Search from start date (YYYY-MM-DD)')
@click.option('--end-date', help='Search until end date (YYYY-MM-DD)')
@click.option('--camera', help='Search by camera model')
@click.option('--output', '-o', type=click.Choice(['table', 'list']), default='table', help='Output format')
def search(db: str, person: str, date: str, start_date: str, end_date: str, camera: str, output: str):
    """
    Search images by person, date, or camera model.

    Examples:
        photosense search --person "Alice"
        photosense search --date "2023-12-25"
        photosense search --start-date "2023-01-01" --end-date "2023-12-31"
        photosense search --camera "iPhone"
        photosense search --person "Bob" --date "2023-06-15"
    """
    try:
        searcher = ImageSearcher(db)

        # Perform search
        results = searcher.search_combined(
            person_name=person,
            date=date,
            start_date=start_date,
            end_date=end_date,
            camera_model=camera
        )

        searcher.close()

        if not results:
            click.echo("No images found matching the search criteria.")
            return

        click.echo(f"Found {len(results)} images:\n")

        if output == 'table':
            # Table format
            click.echo(f"{'Path':<50} {'Date':<12} {'Camera':<20}")
            click.echo("-" * 82)
            for img in results:
                date_str = img.get('date_taken', 'N/A')[:10] if img.get('date_taken') else 'N/A'
                camera_str = img.get('camera_model', 'N/A') or 'N/A'
                path_str = img['file_path'][:47] + "..." if len(img['file_path']) > 50 else img['file_path']
                click.echo(f"{path_str:<50} {date_str:<12} {camera_str:<20}")
        else:
            # List format
            for img in results:
                click.echo(f"Path: {img['file_path']}")
                if img.get('date_taken'):
                    click.echo(f"  Date: {img['date_taken']}")
                if img.get('camera_model'):
                    click.echo(f"  Camera: {img['camera_model']}")
                click.echo()

    except Exception as e:
        logger.error(f"Search failed: {e}")
        sys.exit(1)


@cli.command()
@click.option('--db', default='photosense.db', help='Path to database file')
def list_people(db: str):
    """List all people (clusters) in the database."""
    try:
        db_manager = Database(db)
        people = db_manager.get_all_people()

        if not people:
            click.echo("No people found in database. Run 'cluster' command first.")
            return

        click.echo(f"Found {len(people)} people:\n")
        click.echo(f"{'ID':<5} {'Cluster ID':<12} {'Name':<30}")
        click.echo("-" * 47)

        for person in people:
            person_id = person['id']
            cluster_id = person['cluster_id']
            name = person['name'] or 'Unnamed'
            click.echo(f"{person_id:<5} {cluster_id:<12} {name:<30}")

        db_manager.close()

    except Exception as e:
        logger.error(f"Error listing people: {e}")
        sys.exit(1)


@cli.command()
@click.option('--db', default='photosense.db', help='Path to database file')
@click.option('--person-id', required=True, type=int, help='ID of the person to label')
@click.option('--name', required=True, help='Name to assign to this person')
def label(db: str, person_id: int, name: str):
    """
    Assign a human-readable name to a person (cluster).

    First, use 'list-people' to see all people and their IDs.
    """
    try:
        db_manager = Database(db)

        # Check if person exists
        people = db_manager.get_all_people()
        person_ids = [p['id'] for p in people]

        if person_id not in person_ids:
            click.echo(f"Error: Person ID {person_id} not found.")
            click.echo("Use 'list-people' to see available person IDs.")
            sys.exit(1)

        # Update person name
        db_manager.update_person_name(person_id, name)
        db_manager.close()

        click.echo(f"Successfully labeled person {person_id} as '{name}'")

    except Exception as e:
        logger.error(f"Error labeling person: {e}")
        sys.exit(1)


@cli.command()
@click.option('--db', default='photosense.db', help='Path to database file')
def stats(db: str):
    """Show database statistics."""
    try:
        db_manager = Database(db)
        images = db_manager.get_all_images()
        faces = db_manager.get_all_faces()
        people = db_manager.get_all_people()
        db_manager.close()

        click.echo(f"Database: {db}")
        click.echo(f"Images: {len(images)}")
        click.echo(f"Faces: {len(faces)}")
        click.echo(f"People: {len(people)}")
    except Exception as e:
        logger.error(f"Error getting stats: {e}")
        sys.exit(1)


if __name__ == '__main__':
    cli()
