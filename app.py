"""
Streamlit UI for PhotoSense-AI.

Optional web interface for browsing and managing photos.
"""

import streamlit as st
import sqlite3
from pathlib import Path
from PIL import Image as PILImage
from src.db.database import Database
from src.search.search import ImageSearcher

# Page configuration
st.set_page_config(
    page_title="PhotoSense-AI",
    page_icon="📸",
    layout="wide"
)

# Initialize session state
if 'db_path' not in st.session_state:
    st.session_state.db_path = "photosense.db"


def load_database():
    """Load database connection."""
    try:
        return Database(st.session_state.db_path)
    except Exception as e:
        st.error(f"Error connecting to database: {e}")
        return None


def main():
    """Main Streamlit app."""
    st.title("📸 PhotoSense-AI")
    st.markdown("Offline photo organization with facial recognition")

    # Sidebar
    with st.sidebar:
        st.header("Navigation")
        page = st.radio(
            "Choose a page",
            ["Dashboard", "Search", "People", "Images"]
        )

        st.header("Database")
        db_path = st.text_input("Database path", value=st.session_state.db_path)
        if db_path != st.session_state.db_path:
            st.session_state.db_path = db_path

    # Main content
    if page == "Dashboard":
        show_dashboard()
    elif page == "Search":
        show_search()
    elif page == "People":
        show_people()
    elif page == "Images":
        show_images()


def show_dashboard():
    """Show dashboard with statistics."""
    st.header("Dashboard")

    db = load_database()
    if not db:
        return

    try:
        images = db.get_all_images()
        faces = db.get_all_faces()
        people = db.get_all_people()

        col1, col2, col3 = st.columns(3)

        with col1:
            st.metric("Total Images", len(images))

        with col2:
            st.metric("Detected Faces", len(faces))

        with col3:
            st.metric("People", len(people))

        # Show recent images
        st.subheader("Recent Images")
        if images:
            recent_images = sorted(
                images,
                key=lambda x: x.get('created_at', ''),
                reverse=True
            )[:10]

            cols = st.columns(5)
            for idx, img in enumerate(recent_images):
                col_idx = idx % 5
                with cols[col_idx]:
                    try:
                        if Path(img['file_path']).exists():
                            pil_img = PILImage.open(img['file_path'])
                            st.image(pil_img, use_container_width=True)
                            st.caption(Path(img['file_path']).name)
                        else:
                            st.text("Image not found")
                    except Exception as e:
                        st.text(f"Error: {e}")

    finally:
        db.close()


def show_search():
    """Show search interface."""
    st.header("Search Images")

    db = load_database()
    if not db:
        return

    try:
        searcher = ImageSearcher(st.session_state.db_path)

        # Search form
        with st.form("search_form"):
            col1, col2 = st.columns(2)

            with col1:
                person_name = st.text_input("Person name")
                date = st.text_input("Date (YYYY-MM-DD)")

            with col2:
                start_date = st.text_input("Start date (YYYY-MM-DD)")
                end_date = st.text_input("End date (YYYY-MM-DD)")
                camera = st.text_input("Camera model")

            submitted = st.form_submit_button("Search")

        if submitted:
            results = searcher.search_combined(
                person_name=person_name or None,
                date=date or None,
                start_date=start_date or None,
                end_date=end_date or None,
                camera_model=camera or None
            )

            st.write(f"Found {len(results)} images")

            # Display results
            if results:
                cols = st.columns(4)
                for idx, img in enumerate(results):
                    col_idx = idx % 4
                    with cols[col_idx]:
                        try:
                            if Path(img['file_path']).exists():
                                pil_img = PILImage.open(img['file_path'])
                                st.image(pil_img, use_container_width=True)
                                st.caption(Path(img['file_path']).name)
                                if img.get('date_taken'):
                                    st.caption(f"Date: {img['date_taken'][:10]}")
                            else:
                                st.text("Image not found")
                        except Exception as e:
                            st.text(f"Error: {e}")

        searcher.close()

    except Exception as e:
        st.error(f"Error: {e}")


def show_people():
    """Show people/clusters."""
    st.header("People")

    db = load_database()
    if not db:
        return

    try:
        people = db.get_all_people()

        if not people:
            st.info("No people found. Run 'cluster' command first.")
            return

        # Display people
        for person in people:
            with st.expander(
                f"{person['name'] or 'Unnamed'} (ID: {person['id']}, Cluster: {person['cluster_id']})"
            ):
                # Get faces for this person
                searcher = ImageSearcher(st.session_state.db_path)
                faces = searcher.get_faces_for_person(person['id'])
                searcher.close()

                st.write(f"Faces: {len(faces)}")

                # Show face thumbnails
                if faces:
                    cols = st.columns(5)
                    for idx, face in enumerate(faces[:10]):  # Show first 10
                        col_idx = idx % 5
                        with cols[col_idx]:
                            try:
                                if face.get('face_path') and Path(face['face_path']).exists():
                                    pil_img = PILImage.open(face['face_path'])
                                    st.image(pil_img, use_container_width=True)
                            except Exception as e:
                                st.text("Error")

                # Label person
                with st.form(f"label_form_{person['id']}"):
                    new_name = st.text_input("Name", value=person['name'] or "")
                    if st.form_submit_button("Update Name"):
                        db.update_person_name(person['id'], new_name)
                        st.success("Name updated!")
                        st.rerun()

    finally:
        db.close()


def show_images():
    """Show all images."""
    st.header("All Images")

    db = load_database()
    if not db:
        return

    try:
        images = db.get_all_images()

        if not images:
            st.info("No images found. Run 'scan' command first.")
            return

        # Pagination
        images_per_page = 20
        total_pages = (len(images) + images_per_page - 1) // images_per_page
        page = st.number_input("Page", min_value=1, max_value=total_pages, value=1)

        start_idx = (page - 1) * images_per_page
        end_idx = start_idx + images_per_page
        page_images = images[start_idx:end_idx]

        st.write(f"Showing {start_idx + 1}-{min(end_idx, len(images))} of {len(images)} images")

        # Display images
        cols = st.columns(4)
        for idx, img in enumerate(page_images):
            col_idx = idx % 4
            with cols[col_idx]:
                try:
                    if Path(img['file_path']).exists():
                        pil_img = PILImage.open(img['file_path'])
                        st.image(pil_img, use_container_width=True)
                        st.caption(Path(img['file_path']).name)
                    else:
                        st.text("Image not found")
                except Exception as e:
                    st.text(f"Error: {e}")

    finally:
        db.close()


if __name__ == "__main__":
    main()
