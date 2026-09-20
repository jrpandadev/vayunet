import urllib.request
import os

os.makedirs("data/hard_negatives", exist_ok=True)
os.makedirs("data/dust_construction", exist_ok=True)

negatives = [
    ("https://images.unsplash.com/photo-1499346141975-6c17887dff57?w=800&q=80", "clear_sky.jpg"), # Clear sky
    ("https://images.unsplash.com/photo-1486406146926-c627a92ad1ab?w=800&q=80", "cityscape.jpg")  # Cityscape
]

dust_sites = [
    ("https://images.unsplash.com/photo-1541888081682-965ba3932b13?w=800&q=80", "construction_dust.jpg"), # Construction
    ("https://images.unsplash.com/photo-1504307651254-35680f356f12?w=800&q=80", "construction_clean.jpg") # Construction clean
]

print("Downloading hard negatives...")
for url, filename in negatives:
    path = os.path.join("data/hard_negatives", filename)
    if not os.path.exists(path):
        urllib.request.urlretrieve(url, path)
        print(f"Downloaded {filename}")

print("Downloading construction samples...")
for url, filename in dust_sites:
    path = os.path.join("data/dust_construction", filename)
    if not os.path.exists(path):
        urllib.request.urlretrieve(url, path)
        print(f"Downloaded {filename}")

print("Done.")
