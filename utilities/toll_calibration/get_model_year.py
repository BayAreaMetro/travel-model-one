import os

def get_first_4_digits_of_cwd():
    # Get the current working directory
    cwd = os.getcwd()
    # Extract the base name of the directory
    folder_name = os.path.basename(cwd)
    # Extract the first 4 characters
    first_4_chars = folder_name[:4]
    # Check if the first 4 characters are digits and assert an error if not
    assert first_4_chars.isdigit(), "The first 4 characters of the current working directory's folder name are not numeric."
    return first_4_chars

# Example usage
first_4_digits = get_first_4_digits_of_cwd()
print(first_4_digits)