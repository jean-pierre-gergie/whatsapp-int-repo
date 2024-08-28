from flask import Blueprint, request, render_template, flash, redirect, url_for, current_app
import pandas as pd
import tempfile
import os
from pymongo import MongoClient

bp = Blueprint('upload_data', __name__)
@bp.route('/upload_file', methods=['GET', 'POST'])
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

            column_mapping = dict(zip(csv_columns, db_columns))

            unique_fields = ['first_name', 'last_name', 'mobile','tag']

            mongo_db = current_app.mongo
            collection = mongo_db.members

            for _, row in df.iterrows():
                member_data = {db_col: row[csv_col] for csv_col, db_col in column_mapping.items() if pd.notnull(row[csv_col])}

                if not member_data:
                    continue

                query_filters = {field: member_data[field] for field in unique_fields if field in member_data}

                existing_member = collection.find_one(query_filters)

                if existing_member:
                    print(f"Member already exists: {existing_member}")
                    continue

                collection.insert_one(member_data)

            if 'tag' in column_mapping.values():
                tag_column = list(column_mapping.keys())[list(column_mapping.values()).index('tag')]
                tags = df[tag_column].unique()
                campaign_collection = mongo_db.campaign 
                for tag in tags:
                    if not campaign_collection.find_one({'tag': tag}):
                        campaign_collection.insert_one({'tag': tag})

            os.remove(temp_file_path)

            flash('Data inserted successfully!', 'success')
        except Exception as e:
            flash(f'An error occurred: {str(e)}', 'error')
        finally:
            return redirect(url_for('upload_data.upload_file'))