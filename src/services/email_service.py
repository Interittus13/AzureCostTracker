import webbrowser

# TODO
# Send Emails

def preview_email(html):
    temp_file = "preview.html"
    with open(temp_file, "w", encoding="utf-8") as file:
        file.write(html)

    webbrowser.open(temp_file)