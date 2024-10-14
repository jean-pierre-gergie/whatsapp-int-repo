from flask import Blueprint, request, render_template, flash, redirect, url_for, current_app, jsonify
import pandas as pd
import tempfile
import os
# from pymongo import MongoClient
from flask_jwt_extended import jwt_required, get_jwt_identity
from ..utils.decorators import role_required
from ..utils.helper_functions import check_df_validity
from ..utils.country_number_cleaning import is_valid_phone_number



bp = Blueprint('upload_data', __name__)
@bp.route('/upload_file', methods=['GET', 'POST'])
@jwt_required()
@role_required(['admin', 'user']) 
def upload_file():
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
                                   temp_file_path=temp_file_path)

        except pd.errors.EmptyDataError:
            flash('No columns to parse from file. The file might be empty.', 'error')
            return render_template('upload.html')
        except Exception as e:
            flash(f'An error occurred: {str(e)}', 'error')
            return render_template('upload.html')
    return render_template('upload.html')

@bp.route('/map_columns', methods=['POST'])
@jwt_required()
@role_required(['admin', 'user']) 
def map_columns():
    if request.method == 'POST':
        try:
            csv_columns = request.form.getlist('csv_columns[]')
            db_columns = request.form.getlist('db_columns[]')
            temp_file_path = request.form.get('temp_file_path')

            if not temp_file_path:
                flash('No temporary file path provided!', 'error')
                return redirect(url_for('upload_data.upload_file'))

            if not os.path.exists(temp_file_path):
                flash('File not found or path invalid!', 'error')
                return redirect(url_for('upload_data.upload_file'))

            df = pd.read_csv(temp_file_path)

            if df.empty:
                flash('The uploaded file is empty.', 'error')
                os.remove(temp_file_path)
                return redirect(url_for('upload_data.upload_file'))

            # Map columns based on user selections
            column_mapping = dict(zip(csv_columns, db_columns))
            df = df.rename(columns=column_mapping)

            # Apply the check_df_validity function after the column mapping
            stats, duplicates, cleaned_df = check_df_validity(df)

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
                os.remove(temp_file_path)
                return redirect(url_for('upload_data.upload_file'))

            # Flash the combined statistics message
            flash(stats_message, 'info')

            # Insert cleaned data into MongoDB
            unique_fields = ['first_name', 'last_name', 'mobile', 'tag']

            mongo_db = current_app.mongo
            collection = mongo_db.members

            for _, row in cleaned_df.iterrows():
                member_data = {db_col: row[db_col] for db_col in db_columns if pd.notnull(row[db_col])}

                if not member_data:
                    continue

                query_filters = {field: member_data[field] for field in unique_fields if field in member_data}

                existing_member = collection.find_one(query_filters)

                if existing_member:
                    print(f"Member already exists: {existing_member}")
                    continue

                collection.insert_one(member_data)

            if 'tag' in db_columns:
                tags = cleaned_df['tag'].unique()
                campaign_collection = mongo_db.campaign
                
                duplicate_tags = []
                new_tags = []

                for tag in tags:
                    if campaign_collection.find_one({'tag': tag}):
                        duplicate_tags.append(tag)
                    else:
                        campaign_collection.insert_one({'tag': tag})
                        new_tags.append(tag)

                # Flash a notification for duplicate tags
                if duplicate_tags:
                    flash(f'The following tags already exist and were not inserted: {", ".join(duplicate_tags)}', 'warning')

                # Flash a success message for new tags
                if new_tags:
                    flash(f'New tags inserted successfully: {", ".join(new_tags)}', 'success')
                    flash('Data inserted successfully!', 'success')

            os.remove(temp_file_path)

            # flash('Data inserted successfully!', 'success')
        except Exception as e:
            flash(f'An error occurred: {str(e)}', 'error')
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
        mongo_db = current_app.mongo
        collection = mongo_db.members

        # Check for existing member with the same mobile number
        existing_member = collection.find_one({'mobile': formatted_number})
        if existing_member:
            return {'success': False, 'message': 'A member with this mobile number already exists.'}, 409

        # Insert the new member into the collection
        collection.insert_one(member_data)

        # Update campaign tags if the tag does not already exist in the campaign collection
        campaign_collection = mongo_db.campaign
        if not campaign_collection.find_one({'tag': tag}):
            campaign_collection.insert_one({'tag': tag})

        # Return success response
        return {'success': True, 'message': 'Member added successfully.'}, 201

    except Exception as e:
        # Return error response if an exception occurs
        return {'success': False, 'message': f'An error occurred: {str(e)}'}, 500
    

