from flask import Blueprint, request, render_template, flash, redirect, url_for, current_app, jsonify,send_from_directory,send_file
import pandas as pd
import tempfile
import os
# from pymongo import MongoClient
from flask_jwt_extended import jwt_required, get_jwt_identity
from ..utils.decorators import role_required
from ..utils.helper_functions import check_df_validity
from ..utils.country_number_cleaning import is_valid_phone_number
from ..utils.session_config_helper import get_session_foundation_config
from werkzeug.utils import secure_filename
import logging

logging.basicConfig(level=logging.DEBUG, 
                    format='- %(name)s - %(levelname)s - %(message)s')

logger = logging.getLogger(__name__)

bp = Blueprint('upload_data', __name__)

@bp.route('/upload_file', methods=['GET', 'POST'])
@jwt_required()
@role_required(['admin', 'user']) 
def upload_file():

    session_configs =get_session_foundation_config()
  
    foundation_name = session_configs.get('foundation_name')

    if request.method == 'POST':
        file = request.files.get('file')
        if not file:
            flash('No file selected!', 'error')
            return render_template('upload.html')
        try:
            temp_file = tempfile.NamedTemporaryFile(delete=False, suffix='.csv')
            temp_file_path = temp_file.name
            file.save(temp_file_path)

            print(f"Temporary file created at: {temp_file_path}")

            df = pd.read_csv(temp_file_path)

            if df.empty:
                flash('The uploaded file is empty.', 'error')
                os.remove(temp_file_path)
                return render_template('upload.html')

            df_preview = df.head(10)

            csv_columns = df.columns.tolist()
            db_columns = ['id', 'first_name', 'last_name', 'mobile', 'code', 'tag', 'middle_name']

            # Convert only the first 10 rows to HTML
            csv_data_html = df_preview.to_html(classes='data', header="true", index=False)

            return render_template('mapping.html', 
                                   csv_columns=csv_columns, 
                                   db_columns=db_columns, 
                                   csv_data=csv_data_html, 
                                   temp_file_path=temp_file_path,
                                   foundation_name= foundation_name)

        except pd.errors.EmptyDataError:
            flash('No columns to parse from file. The file might be empty.', 'error')
            return render_template('upload.html')
        except Exception as e:
            flash(f'An error occurred while uploading file : {str(e)}', 'error')
            return render_template('upload.html')
    return render_template('upload.html',foundation_name= foundation_name)


@bp.route('/download_sample', methods=['GET'])
@jwt_required()
@role_required(['admin', 'user'])
def download_sample():
    try:
        filename = secure_filename('sample-data.csv')
        file_path = os.path.join('/app', 'sample_member_data', filename)
        if os.path.isfile(file_path):
            # flash('Sample downloaded', 'info')
            return send_file(file_path, as_attachment=True)
        else:
            flash('Sample data file not found!', 'error')
            return redirect(url_for('upload_data.upload_file'))
    except Exception as e:
        flash(f'Error: {str(e)}', 'error')
        return redirect(url_for('upload_data.upload_file'))

    

@bp.route('/map_columns', methods=['POST'])
@jwt_required()
@role_required(['admin', 'user'])
def map_columns():
    if request.method == 'POST':
        try:
            logger.info("Processing /map_columns request.")

            csv_columns = request.form.getlist('csv_columns[]')
            db_columns = request.form.getlist('db_columns[]')
            temp_file_path = request.form.get('temp_file_path')

            logger.debug(f"Received csv_columns: {csv_columns}")
            logger.debug(f"Received db_columns: {db_columns}")
            logger.debug(f"Temporary file path: {temp_file_path}")

            if not temp_file_path:
                flash('No temporary file path provided!', 'error')
                logger.error('No temporary file path provided.')
                return redirect(url_for('upload_data.upload_file'))

            if not os.path.exists(temp_file_path):
                flash('File not found or path invalid!', 'error')
                logger.error(f"File not found at path: {temp_file_path}")
                return redirect(url_for('upload_data.upload_file'))

            logger.info(f"Reading CSV file from: {temp_file_path}")
            df = pd.read_csv(temp_file_path, keep_default_na=False)

            if df.empty:
                flash('The uploaded file is empty.', 'error')
                logger.error("Uploaded CSV file is empty.")
                os.remove(temp_file_path)
                return redirect(url_for('upload_data.upload_file'))

            # Map columns based on user selections
            column_mapping = dict(zip(csv_columns, db_columns))
            logger.info(f"Column mapping: {column_mapping}")
            df = df.rename(columns=column_mapping)

            # Apply the check_df_validity function after the column mapping
            logger.info("Validating DataFrame...")
            stats, duplicates, cleaned_df = check_df_validity(df)

            # Log statistics
            logger.info(f"Stats: {stats}")
            logger.info(f"Number of duplicate rows: {duplicates.shape[0]}")

            # Combine the stats into a single message
            stats_message = (
                f"Total rows: {stats['total_rows']}<br>"
                f"Duplicate rows: {stats['num_duplicates']}<br>"
                f"Invalid phone numbers: {stats['num_invalid_numbers']}<br>"
                f"Valid rows: {stats['num_proper_rows']}"
            )

            # If no valid rows are left after cleaning
            if stats['num_proper_rows'] == 0:
                flash('No valid rows to process after cleaning the data.', 'error')
                logger.warning("No valid rows left after cleaning.")
                os.remove(temp_file_path)
                return redirect(url_for('upload_data.upload_file'))

            # Flash the combined statistics message
            flash(stats_message, 'info')

            # Insert cleaned data into MongoDB
            unique_fields = ['first_name', 'last_name', 'mobile', 'tag']

            session_configs =get_session_foundation_config()

            whatsapp_data_db = session_configs.get('whatsapp_data_db')
            collection = whatsapp_data_db.members

            logger.info("Starting insertion of cleaned data into MongoDB...")
            for _, row in cleaned_df.iterrows():
                member_data = {db_col: row[db_col] for db_col in db_columns if pd.notnull(row[db_col])}
                logger.debug(f"Member data: {member_data}")
                if not member_data:
                    logger.debug("Empty member data, skipping this row.")
                    continue

                query_filters = {field: member_data[field] for field in unique_fields if field in member_data}
                existing_member = collection.find_one(query_filters)

                if existing_member:
                    logger.info(f"Member already exists: {existing_member}")
                    continue

                collection.insert_one(member_data)
                logger.info(f"Inserted member data: {member_data}")

            if 'tag' in db_columns:
                tags = cleaned_df['tag'].unique()
                campaign_collection = whatsapp_data_db.campaign
                
                duplicate_tags = []
                new_tags = []

                for tag in tags:
                    if campaign_collection.find_one({'tag': tag}):
                        duplicate_tags.append(tag)
                        logger.info(f"Duplicate tag found: {tag}")
                    else:
                        campaign_collection.insert_one({'tag': tag})
                        new_tags.append(tag)
                        logger.info(f"Inserted new tag: {tag}")

                # Flash a notification for duplicate tags
                if duplicate_tags:
                    flash(f'The following tags already exist and were not inserted: {", ".join(duplicate_tags)}', 'warning')

                # Flash a success message for new tags
                if new_tags:
                    flash(f'New tags inserted successfully: {", ".join(new_tags)}', 'success')

            logger.info("Finished processing, removing temporary file.")
            os.remove(temp_file_path)

        except Exception as e:
            flash(f'An error occurred while mapping : {str(e)}', 'error')
            logger.error(f"Error while mapping columns: {str(e)}", exc_info=True)
        finally:
            return redirect(url_for('upload_data.upload_file'))
        
@bp.route('/add_member', methods=['POST'])
@jwt_required()
@role_required(['admin', 'user'])
def add_member():
    try:
        # Get form data
        first_name = request.form.get('first_name')
        middle_name = request.form.get('middle_name', '')
        last_name = request.form.get('last_name')
        tag = request.form.get('tag')
        code = request.form.get('code', '')  # Make code optional
        mobile = request.form.get('mobile')

        # Validate the required data
        if not all([first_name, last_name, tag, mobile]):
            return {'success': False, 'message': 'First name, last name, tag, and mobile are required fields.'}, 400

        # Validate the phone number
        formatted_number = is_valid_phone_number(mobile)
        if not formatted_number:
            return {'success': False, 'message': 'Invalid phone number.'}, 400

        # Create the member object with the formatted mobile number
        member_data = {
            'first_name': first_name,
            'middle_name': middle_name,
            'last_name': last_name,
            'tag': tag,
            'code': code,
            'mobile': formatted_number
        }

        # Connect to MongoDB and get the members collection
        session_configs =get_session_foundation_config()

        whatsapp_data_db = session_configs.get('whatsapp_data_db')

        collection = whatsapp_data_db.members

        # Check for existing member with the same mobile number
        existing_member = collection.find_one({'mobile': formatted_number, 'tag': tag})
        if existing_member:
            return {'success': False, 'message': 'A member with this mobile number and tag already exists.'}, 409

        # Insert the new member into the collection
        collection.insert_one(member_data)

        # Update campaign tags if the tag does not already exist in the campaign collection
        campaign_collection = whatsapp_data_db.campaign

        if not campaign_collection.find_one({'tag': tag}):
            campaign_collection.insert_one({'tag': tag})

        # Return success response
        return {'success': True, 'message': 'Member added successfully.'}, 201

    except Exception as e:
        # Return error response if an exception occurs
        return {'success': False, 'message': f'An error occurred: {str(e)}'}, 500
    

