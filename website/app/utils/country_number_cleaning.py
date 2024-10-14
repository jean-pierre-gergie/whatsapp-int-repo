import phonenumbers
import pandas as pd 
import json
import re 
import logging
import os 

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')



def load_dict(json_file):
    with open(json_file, 'r') as f:
        return json.load(f)


def load_digits_mapping():
    base_path = os.path.dirname(__file__)  # Get the directory of the current script
    
    # Construct full paths to each JSON file
    one_digits_path = os.path.join(base_path, 'digit_mapping', 'one_digits.json')
    two_digits_path = os.path.join(base_path, 'digit_mapping', 'two_digits.json')
    three_digits_path = os.path.join(base_path, 'digit_mapping', 'three_digits.json')
    four_digits_path = os.path.join(base_path, 'digit_mapping', 'four_digits.json')
    five_digits_path = os.path.join(base_path, 'digit_mapping', 'five_digits.json')
    
    # Load the JSON data from each file
    with open(one_digits_path, 'r') as f:
        one_digits = json.load(f)
    with open(two_digits_path, 'r') as f:
        two_digits = json.load(f)
    with open(three_digits_path, 'r') as f:
        three_digits = json.load(f)
    with open(four_digits_path, 'r') as f:
        four_digits = json.load(f)
    with open(five_digits_path, 'r') as f:
        five_digits = json.load(f)
    
    return one_digits, two_digits, three_digits, four_digits, five_digits



def strip_leading_non_digits_and_remove_00(s):
    # Remove all leading non-digit characters
    stripped_string = re.sub(r'^\D+', '', s)
    
    # Remove leading "00" if present
    if stripped_string.startswith("00"):
        stripped_string = stripped_string[2:]
    
    return stripped_string


def get_country_code_from_digits(phone_number,one_digits, two_digits, three_digits, four_digits,five_digits):
    
    one_digits, two_digits, three_digits, four_digits,five_digits = load_digits_mapping()
    
    if phone_number is None:
        return None

    # # phone_number = phone_number.lstrip('+')  # Remove leading '+' if present
    # phone_number = f"+{phone_number}"        # Add the '+' at the beginning
    # # Check in order from 4 digits to 1 digit
    if len(phone_number) >= 5 and phone_number[:5] in five_digits:
        return f"{phone_number[:5]}"
    elif len(phone_number) >= 4 and phone_number[:4] in four_digits:
        return f"{phone_number[:4]}"
    elif len(phone_number) >= 3 and phone_number[:3] in three_digits:
        return f"{phone_number[:3]}"
    elif len(phone_number) >= 2 and phone_number[:2] in two_digits:
        return f"{phone_number[:2]}"
    elif len(phone_number) >= 1 and phone_number[:1] in one_digits:
        return f"{phone_number[:1]}"
    
    return None



# Function to get the country abbreviation from a country code
def get_abbrev_from_country_code(country_code):
    # Get the current script's directory
    base_path = os.path.dirname(__file__)
    
    # Construct the full path to the country mapping file
    country_to_country_code_mapping_file = os.path.join(base_path, 'country_mapping', 'country_country_code_map.json')
    
    # Load the country code mapping
    country_to_country_code_mapping = load_dict(country_to_country_code_mapping_file)
    
    # Find the matching country abbreviation
    for country_abbr, code in country_to_country_code_mapping.items():
        if code == f"+{country_code}":
            return country_abbr
    
    return None


def is_valid_phone_number(number):
    try:
        logging.info(f"Received phone number: {number}")
        
        # Strip leading non-digits and remove leading 00
        number = strip_leading_non_digits_and_remove_00(number)
        logging.debug(f"Processed number after stripping: {number}")

        # Load digit mappings
        one_digits, two_digits, three_digits, four_digits, five_digits = load_digits_mapping()
        # logging.debug(f"Loaded digit mappings: {one_digits}, {two_digits}, {three_digits}, {four_digits}, {five_digits}")

        # Get country code from digits
        country_code = get_country_code_from_digits(number, one_digits, two_digits, three_digits, four_digits, five_digits)
        logging.debug(f"Extracted country code: {country_code}")

        # Get country abbreviation from country code
        country_abbr = get_abbrev_from_country_code(country_code)
        logging.debug(f"Country abbreviation: {country_abbr}")

        # Parse the phone number using the country abbreviation
        parsed_number = phonenumbers.parse(number, country_abbr)
        logging.debug(f"Parsed phone number: {parsed_number}")

        # Check if the number is valid
        if not phonenumbers.is_valid_number(parsed_number):
            logging.warning(f"Invalid phone number: {number}")
            return None

        # Format the number to international format
        formatted_number = phonenumbers.format_number(parsed_number, phonenumbers.PhoneNumberFormat.E164).replace("+", "")
        logging.info(f"Formatted phone number: {formatted_number}")

        # Return the formatted number
        return formatted_number

    except phonenumbers.NumberParseException as e:
        logging.error(f"Error parsing phone number {number}: {str(e)}")
        return None






