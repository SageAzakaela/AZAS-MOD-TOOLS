import xml.etree.ElementTree as ET
import random
import os
import tkinter as tk
from tkinter import filedialog
from PIL import Image
import numpy as np
from collections import deque

class MapEditorApp:
    def __init__(self, master):
        self.master = master
        self.master.title("Map Editor")

        self.map_folder_path = ""
        self.tbx_files = []
        self.water_image_path = ""

        # GUI components
        self.label_map_folder = tk.Label(master, text="Select Map Folder:")
        self.label_tbx_files = tk.Label(master, text="Select TBX Files:")
        self.label_water_image = tk.Label(master, text="Select Terrain Image:")

        self.button_browse_map_folder = tk.Button(master, text="Browse", command=self.browse_map_folder)
        self.button_browse_tbx_files = tk.Button(master, text="Browse", command=self.browse_tbx_files)
        self.button_browse_water_image = tk.Button(master, text="Browse", command=self.browse_water_image)

        self.button_process = tk.Button(master, text="Process", command=self.process_files)

        # Layout
        self.label_map_folder.grid(row=0, column=0, sticky="e")
        self.label_tbx_files.grid(row=1, column=0, sticky="e")
        self.label_water_image.grid(row=2, column=0, sticky="e")

        self.button_browse_map_folder.grid(row=0, column=1)
        self.button_browse_tbx_files.grid(row=1, column=1)
        self.button_browse_water_image.grid(row=2, column=1)

        self.button_process.grid(row=3, column=0, columnspan=2)

    def browse_map_folder(self):
        self.map_folder_path = filedialog.askdirectory()
        print(f"Selected Map Folder: {self.map_folder_path}")

    def browse_tbx_files(self):
        tbx_file_paths = filedialog.askopenfilenames(filetypes=[("TBX Files", "*.tbx")])
        self.tbx_files = list(tbx_file_paths)
        print(f"Selected TBX Files: {self.tbx_files}")

    def browse_water_image(self):
        self.water_image_path = filedialog.askopenfilename(filetypes=[("Image Files", "*.png;*.jpg;*.jpeg")])
        print(f"Selected Water Image: {self.water_image_path}")

    def process_files(self):
        if not self.map_folder_path or not self.tbx_files or not self.water_image_path:
            print("Please select the map folder, TBX files, and water image.")
            return

        # Load water image
        water_image = Image.open(self.water_image_path)

        # Process map files
        for map_file_name in os.listdir(self.map_folder_path):
            if map_file_name.endswith(".pzw"):
                map_file_path = os.path.join(self.map_folder_path, map_file_name)
                self.process_map_file(map_file_path, water_image)

        print("Processing complete.")

    def process_map_file(self, map_file_path, water_image):
        try:
            tree = ET.parse(map_file_path)
            root = tree.getroot()

            # Randomly shuffle the TBX files to ensure randomness
            random.shuffle(self.tbx_files)

            # Keep track of placed buildings
            placed_buildings = set()

            # Assuming the 'cell' element is directly under the root
            for cell in root.findall(".//cell"):
                # Iterate over TBX files
                for tbx_file in self.tbx_files:
                    # Check if we already placed this building
                    if tbx_file in placed_buildings:
                        continue

                    # Get building dimensions from the current TBX file
                    building_width, building_height = self.get_building_dimensions(tbx_file)

                    # Try to add a random lot to the cell
                    if self.add_random_lot_to_cell(cell, building_width, building_height, water_image):
                        # Mark this building as placed
                        placed_buildings.add(tbx_file)

                        # Print the details of the placed building
                        print(f"Building placed in cell: {cell.get('x')}, {cell.get('y')}")
                        print(f"Building dimensions: {building_width} x {building_height}")
                        print(f"Building file: {tbx_file}")

            # Save the modified tree back to the PZW file
            tree.write(map_file_path)
            print(f"Processing complete. Modified PZW file saved at: {map_file_path}")

        except ET.ParseError as e:
            print(f"Error parsing XML file: {e}")
        except Exception as e:
            print(f"An error occurred: {e}")

    def add_random_lot_to_cell(self, cell, building_width, building_height, water_image):
        cell_width = int(cell.get('width', 300))
        cell_height = int(cell.get('height', 300))

        # Use a queue to keep track of buildings to be placed
        building_queue = deque(self.tbx_files)

        # Use a set to track which buildings have been placed
        placed_buildings = set()

        print("Building queue:", building_queue)

        while building_queue:
            current_building = random.choice(list(building_queue))

            lot_x = random.randint(0, cell_width - building_width)
            lot_y = random.randint(0, cell_height - building_height)

            print(f"Trying to place building {current_building} at coordinates ({lot_x}, {lot_y})")

            # Check if there is water in the chosen lot coordinates
            if not self.check_water_in_lot(lot_x, lot_y, building_width, building_height, cell, water_image):
                # Check if there is already a building in the chosen lot coordinates
                if not self.check_building_in_lot(lot_x, lot_y, building_width, building_height, cell):
                    new_lot = ET.Element("lot", {"x": str(lot_x), "y": str(lot_y), "width": str(building_width),
                                                "height": str(building_height), "map": current_building})
                    cell.append(new_lot)

                    # Remove the placed building from the queue and mark it as placed
                    building_queue.remove(current_building)
                    placed_buildings.add(current_building)

                    print(f"Building {current_building} placed at coordinates ({lot_x}, {lot_y})")
                else:
                    print("Cannot place building, another building already exists in the chosen lot")
            else:
                print("Cannot place building, water present in the chosen lot")

            # Check if there are no more buildings left to place
            if not building_queue:
                print("No more buildings left to place, breaking out of loop")
                break

        # Clear the placed buildings set for the next iteration (if any)
        placed_buildings.clear()


    def check_building_in_lot(self, lot_x, lot_y, building_width, building_height, cell):
        # Iterate over the existing 'lot' elements in the cell
        for lot in cell.findall(".//lot"):
            x = int(lot.get('x', 0))
            y = int(lot.get('y', 0))
            width = int(lot.get('width', 0))
            height = int(lot.get('height', 0))

            # Check if the current lot overlaps with the chosen lot coordinates
            if (lot_x < x + width and lot_x + building_width > x and
                    lot_y < y + height and lot_y + building_height > y):
                return True  # There is an overlap with an existing building

        return False  # No overlap with existing buildings

    def check_water_in_lot(self, lot_x, lot_y, building_width, building_height, cell, water_image):
        # Extract cell coordinates and dimensions
        x = int(cell.get('x', 0))
        y = int(cell.get('y', 0))

        # Calculate the coordinates within the cell
        x_within_cell = x + lot_x
        y_within_cell = y + lot_y

        # Crop the water image to match the lot dimensions
        cropped_water_image = water_image.crop((x_within_cell, y_within_cell,
                                                x_within_cell + building_width, y_within_cell + building_height))

        # Convert the cropped image to a numpy array
        image_array = np.array(cropped_water_image)

        # Define the water colors to check
        water_colors = [
            np.array([0, 138, 255]),  # (0, 138, 255) - Standard water color
            np.array([100, 100, 100]), # (100, 100, 100) - Additional color 1
            np.array([120, 120, 120])  # (120, 120, 120) - Additional color 2
        ]

        # Check if any pixel in the image matches any of the water colors
        for color in water_colors:
            if np.any(np.all(image_array == color, axis=-1)):
                return True  # Found water color match

        return False  # No water color match


    def get_building_dimensions(self, tbx_file):
        try:
            tree = ET.parse(tbx_file)
            root = tree.getroot()

            # Assuming the 'building' element is the root
            width = int(root.get('width', 0))
            height = int(root.get('height', 0))

            return width, height

        except ET.ParseError as e:
            print(f"Error parsing XML file: {e}")
            return 0, 0


if __name__ == "__main__":
    root = tk.Tk()
    app = MapEditorApp(root)
    root.mainloop()
