import uuid
import segno
from PIL import Image, ImageDraw, ImageFont
import random
import string
import os

def generate_ticket_image(unique_id, shownumber, date, time):
    # Create a QR code
    link="tickets.tsirk.be/ticket?id="
    qr_file = "temp_qr.png"
    qr = segno.make(link+unique_id)
    qr.save(qr_file, scale=1, border=0, dark='#EEEEEE', light=None)  # 'light=None' removes the background

    # Resize the QR code to 150x150 pixels
    qr_image = Image.open(qr_file)
    qr_image = qr_image.resize((100, 100), Image.Resampling.LANCZOS)
    qr_image.save(qr_file)

    # Open the template image
    template = Image.open("ticket-template.jpg").convert("RGBA")

    # Open the QR code image
    qr_image = Image.open(qr_file).convert("RGBA")

    # Paste the QR code onto the template at position (400, 225)
    template.paste(qr_image, (350, 640), qr_image)

    # Load the font
    font = ImageFont.truetype("fonts/Rubik-light.ttf", size=30)
    font_bold = ImageFont.truetype("fonts/Rubik-bold.ttf", size=35)

    # Create a drawing context
    draw = ImageDraw.Draw(template)


    draw.text((285, 590), f"{date} MAART 2026", font=font_bold, fill=None, stroke_width=0, stroke_fill="white", align="center", anchor="mm")
    draw.text((200, 700), f"SHOW {shownumber}\n{time}", font=font, fill=None, stroke_width=0, stroke_fill="white", align="center", anchor="mm")
    draw.text((400, 760), f"{unique_id}", font=font, fill=None, stroke_width=0, stroke_fill="white", align="center", anchor="mm")

    # Halve the size of the final image
    # final_image = template.resize((template.width // 2, template.height // 2), Image.Resampling.LANCZOS)
    final_image = template

    output_dir = "assets/tickets"
    os.makedirs(output_dir, exist_ok=True)
    # Save the halved image as a JPEG
    output_file_jpeg = f"{output_dir}/{unique_id}.jpeg"
    final_image.convert("RGB").save(output_file_jpeg, "JPEG")

    # # Save the final image with the UUID as the name
    # output_file = f"{output_dir}/{unique_id}.png"
    # template.save(output_file)

    # Remove the temporary QR code file
    os.remove(qr_file)

    print(f"QR code generated for UUID: {unique_id}")
    print(f"Final image saved as: {output_file_jpeg}")

# # Example usage
# unique_id = str(uuid.uuid4())
# generate_ticket_image(unique_id)


if __name__ == "__main__":
    generate_ticket_image("ABCDEF", 1, 28, "13u30")
