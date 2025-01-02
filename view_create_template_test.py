

# Backend Changes Highlighted
@bp.route('/create_template', methods=['POST'])
@jwt_required()
@role_required(['admin', 'user'])
def create_template():
    current_user = get_jwt_identity()
    logger.debug(f"Current user: {current_user}")

    session_configs = get_session_foundation_config()
    api_key_360 = session_configs.get('api_key')

    try:
        # Extract form data
        template_name = request.form['template_name']
        category = request.form['category']
        language_code = request.form['language']
        header_type = request.form.get('header_type')
        header_text = request.form.get('header_text')
        header_image_url = request.form.get('header_image_url')
        header_video_url = request.form.get('header_video_url')  # Highlighted Change
        body_text = request.form['body_text']
        body_examples = request.form.getlist('body_example')
        footer_text = request.form.get('footer_text')
        allow_category_change = request.form.get('allow_category_change') == 'on'

        # Buttons logic
        buttons = []
        button_types = request.form.getlist('button_type')
        button_texts = request.form.getlist('button_text')
        phone_numbers = request.form.getlist('phone_number')
        urls = request.form.getlist('url')

        for i in range(len(button_types)):
            if button_types[i]:
                button_data = {"type": button_types[i], "text": button_texts[i]}
                if button_types[i] == "PHONE_NUMBER" and i < len(phone_numbers):
                    button_data["phone_number"] = phone_numbers[i]
                elif button_types[i] == "URL" and i < len(urls):
                    button_data["url"] = urls[i]
                buttons.append(button_data)

        # Components logic
        components = []

        # Header Component
        if header_type == 'TEXT' and header_text:
            components.append({
                "type": "HEADER",
                "format": "TEXT",
                "text": header_text
            })
        elif header_type == 'IMAGE' and header_image_url:
            components.append({
                "type": "HEADER",
                "format": "IMAGE",
                "example": {"header_handle": [header_image_url]}
            })
        elif header_type == 'VIDEO' and header_video_url:  # Highlighted Change
            components.append({
                "type": "HEADER",
                "format": "VIDEO",
                "example": {"header_handle": [header_video_url]}
            })

        # Body Component
        if body_text:
            variables = [part for part in body_text.split() if part.startswith('{{') and part.endswith('}}')]
            num_variables = len(variables)
            examples = [body_examples[i:i + num_variables] for i in range(0, len(body_examples), num_variables)]
            components.append({
                "type": "BODY",
                "text": body_text,
                "example": {"body_text": examples} if examples else None
            })

        # Footer Component
        if footer_text:
            components.append({"type": "FOOTER", "text": footer_text})

        # Buttons Component
        if buttons:
            components.append({"type": "BUTTONS", "buttons": buttons})

        # Create Template Data
        template_data = {
            "name": template_name,
            "category": category,
            "language": language_code,
            "components": components,
            "allow_category_change": allow_category_change
        }

        # Send API Request
        headers = {
            "Content-Type": "application/json",
            "D360-API-KEY": api_key_360
        }
        response = requests.post("https://waba-v2.360dialog.io/v1/configs/templates", headers=headers, json=template_data)
        response_data = response.json()

        if response_data.get('status') in ['submitted', 'pending']:
            return jsonify(
                template_data=template_data,
                message="Template created and is pending approval",
                api_response=response_data
            ), 200
        else:
            error_message = response_data.get('meta', {}).get('developer_message', 'An error occurred.')
            return jsonify(
                status_code=response.status_code,
                response=response_data,
                error_message=error_message
            ), 400

    except Exception as e:
        logger.exception("An unexpected error occurred during template creation")
        return jsonify(message="An error occurred while creating the template", error=str(e)), 500
