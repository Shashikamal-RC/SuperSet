import os
import time
import streamlit as st
import io
from datetime import datetime
from services.gemini_extractor import extract_job_details
from services.google_sheet_logger import log_job_data  # Using the new helper function
from services.slack_notifier import send_slack_notification
from services.automate_poster_v1 import JobData, SupersetAutomator
import PyPDF2
import docx

# Slack Token (you can set this as an environment variable or store it securely)
SLACK_TOKEN = "your-slack-token"  # Replace with your actual Slack token
SLACK_CHANNEL = "#general"  # Replace with your Slack channel


st.set_page_config(page_title="Smart Job poster", layout="wide")
st.title("🤖 Smart Job Poster")
st.markdown("Paste job-related text and/or upload a file below. We'll extract a clean job description for you.")

# Always show text area for input
user_input = st.text_area("Paste Raw Input (Optional)", height=200, placeholder="Paste the job-related content here...")

# Also always show file upload option
st.markdown("### Upload Job Description Document (Optional)")
uploaded_file = st.file_uploader("Upload PDF or Word document", type=["pdf", "docx"], help="Upload a PDF or Word document")

# Variable to store file content
file_content = ""

# Extract text from the uploaded file when a file is provided
if uploaded_file is not None:
    try:
        with st.spinner("Reading file content..."):
            if uploaded_file.name.endswith('.pdf'):
                # Read PDF file
                pdf_reader = PyPDF2.PdfReader(io.BytesIO(uploaded_file.read()))
                file_content = ""
                for page in pdf_reader.pages:
                    file_content += page.extract_text() + "\n"
            elif uploaded_file.name.endswith('.docx'):
                # Read Word file
                doc = docx.Document(io.BytesIO(uploaded_file.read()))
                file_content = "\n".join([paragraph.text for paragraph in doc.paragraphs])
            
            if file_content.strip():
                st.success(f"✅ Successfully read content from {uploaded_file.name}")
                # Display a preview of the extracted text
                with st.expander("Preview extracted text from file"):
                    st.text(file_content[:500] + ("..." if len(file_content) > 500 else ""))
            else:
                st.warning("Could not extract text from the file. The file might be empty or formatted unusually.")
    except Exception as e:
        st.error(f"❌ Error reading file: {str(e)}")
        file_content = ""

# Initialize session state
if "job_data" not in st.session_state:
    st.session_state.job_data = None

# Extract job details
if st.button("Extract Job Details"):
    # Combine text input and file content
    combined_input = user_input + "\n\n" + file_content if file_content else user_input
    
    if not combined_input.strip():
        st.warning("Please provide input either by pasting text or uploading a file.")
    else:
        try:
            with st.spinner("Extracting details... Please wait."):
                st.session_state.job_data = extract_job_details(combined_input)

            st.success("✅ Job details extracted successfully!")
        except Exception as e:
            st.error(f"❌ Error during extraction: {str(e)}")

# Show extracted data
if st.session_state.job_data:
    st.subheader("Review and Edit Job Details")
    
    # Create form for editing job details
    with st.form("job_details_form"):
        # User who is posting the job
        posted_by = st.text_input("Posted by *", "Rishikesh")
        
        # Mandatory fields (marked with *)
        company_name = st.text_input("Company Name *", 
                                    value=st.session_state.job_data.get('company_name', ''))
        job_title = st.text_input("Job Title *", 
                                value=st.session_state.job_data.get('job_title', ''))
        location = st.text_input("Location *", 
                                value=st.session_state.job_data.get('location', 'Pune'))
        
        job_function = st.selectbox(
            "Job Function *",
            options=["Software Development", "Sales", "General Management", "Marketing - General", "Product Management"],
            index=0 if st.session_state.job_data.get('job_function', '') not in [
                "Software Development", "Sales", "General Management", "Marketing - General", "Product Management"
            ] else ["Software Development", "Sales", "General Management", "Marketing - General", "Product Management"].index(
                st.session_state.job_data.get('job_function', "Software Development")
            )
        )

        min_salary = st.text_input("Minimum Salary *", 
                                value=str(st.session_state.job_data.get('min_salary', '1000000')))
        max_salary = st.text_input("Maximum Salary *", 
                                value=str(st.session_state.job_data.get('max_salary', '1500000')))
        
        # Optional fields
        job_description = st.text_area("Job Description", 
                                    value=st.session_state.job_data.get('job_description', ''), 
                                    height=200)
        salary_breakup = st.text_area("Salary Breakup", 
                                     value=st.session_state.job_data.get('salary_breakup', ''),
                                     height=100)
                                     
        # AI generated flag
        is_ai_generated = st.checkbox("JD Generated by AI", 
                                     value=st.session_state.job_data.get('is_ai_generated', False))
        
        # Check if all mandatory fields are filled
        mandatory_fields_filled = (
            posted_by != '' and
            company_name != '' and 
            job_title != '' and 
            location != '' and 
            min_salary != '' and 
            max_salary != ''
        )
        
        # Update session state with form values
        if st.form_submit_button("Update Details"):
            st.session_state.username = posted_by  # Save username for future use
            
            # Create structured data using our enhanced JobData class
            updated_data = {
                'company_name': company_name,
                'job_title': job_title,
                'location': location,
                'job_function': job_function,
                'min_salary': int(min_salary) if min_salary.isdigit() else 0,
                'max_salary': int(max_salary) if max_salary.isdigit() else 0,
                'job_description': job_description,
                'salary_breakup': salary_breakup,
                'is_ai_generated': is_ai_generated,
                'posted_by': posted_by,
                'timestamp': datetime.now()
            }
            
            st.session_state.job_data = updated_data
            st.success("Job details updated!")
    
    # Confirm & Proceed button (outside the form)
    if mandatory_fields_filled:
        if st.button("✅ Confirm & Proceed", key="confirm_proceed"):
            # Create JobData object from the session state data
            job_data_obj = JobData(
                company_name=st.session_state.job_data["company_name"],
                job_title=st.session_state.job_data["job_title"],
                location=st.session_state.job_data["location"],
                min_salary=st.session_state.job_data["min_salary"],
                max_salary=st.session_state.job_data["max_salary"],
                job_description=st.session_state.job_data["job_description"],
                job_function=st.session_state.job_data["job_function"],
                salary_breakup=st.session_state.job_data["salary_breakup"],
                is_ai_generated=st.session_state.job_data["is_ai_generated"],
                posted_by=st.session_state.job_data.get("posted_by", "Rishikesh"),
                timestamp=st.session_state.job_data.get("timestamp", datetime.now())
            )            # Job Posting Function
            with st.spinner("Posting Job at SuperSet..."):
                automator = SupersetAutomator(
                    url="https://app.joinsuperset.com/",
                    username="rishikesh@mesaschool.co",
                    password="@Mesa2025",
                    headless=os.getenv("HEADLESS", "False").lower() in ("true", "1", "t")
                )
                posting_success = automator.run(job_data_obj)
                
            # Check posting status and proceed accordingly
            if posting_success:
                st.success("📡 Job post successful!")
                
                # Only proceed with logging and notifications if posting succeeds
                # Call logging function
                with st.spinner("Logging to Google Sheet..."):
                    # Log JobData object directly
                    log_success = log_job_data(job_data_obj)
                    if log_success:
                        st.success("📝 Logged in Google Sheet successfully!")
                    else:
                        st.error("❌ Failed to log to Google Sheet.")
                        
                # Option to send Slack notification - only if posting was successful
                with st.spinner("Sending Slack notification..."):
                    message = f"""
                    New job posted by {job_data_obj.posted_by} for {job_data_obj.job_title}
                    at {job_data_obj.company_name}.
                    Location: {job_data_obj.location}.
                    CTC Range: {job_data_obj.min_salary} - {job_data_obj.max_salary}.
                    """
                    if job_data_obj.is_ai_generated:
                        message += " The JD was generated by AI."

                    slack_response = send_slack_notification(message, SLACK_TOKEN, SLACK_CHANNEL)
                    
                    if slack_response:
                        st.success("📢 Slack notification sent successfully!")
                    else:
                        st.error("❌ Failed to send Slack notification.")
    else:
        st.warning("Please fill in all mandatory fields (marked with *) to proceed")
        st.button("✅ Confirm & Proceed", key="confirm_proceed_disabled", disabled=True)
