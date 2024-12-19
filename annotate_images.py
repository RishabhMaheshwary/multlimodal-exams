import tkinter as tk
from tkinter import simpledialog
from PIL import Image, ImageTk
import json
import os

class ImageCropper:
    def __init__(self, root, image_path, output_dir, example):
        self.root = root
        self.root.title("PDF Image Cropper")
        
        # Make the window bigger
        self.root.geometry("1200x800")
        
        # Scrollbars and Canvas
        self.frame = tk.Frame(root)
        self.frame.pack(fill="both", expand=True)
        
        self.v_scroll = tk.Scrollbar(self.frame, orient="vertical")
        self.h_scroll = tk.Scrollbar(self.frame, orient="horizontal")
        
        self.canvas = tk.Canvas(self.frame, 
                                yscrollcommand=self.v_scroll.set, 
                                xscrollcommand=self.h_scroll.set)
        
        self.v_scroll.config(command=self.canvas.yview)
        self.h_scroll.config(command=self.canvas.xview)
        
        self.v_scroll.pack(side="right", fill="y")
        self.h_scroll.pack(side="bottom", fill="x")
        self.canvas.pack(fill="both", expand=True)

        # Variables for cropping
        self.rect = None
        self.start_x = None
        self.start_y = None
        self.crop_coords = []
        self.metadata = []

        self.image_path = image_path
        self.output_dir = output_dir
        self.example = example
        os.makedirs(os.path.join(self.output_dir, "crops"), exist_ok=True)  # Ensure output directory exists
        
        # Load image
        self.load_image()

        # Buttons
        tk.Button(root, text="Save Crops", command=self.save_crops).pack(pady=10)

    def load_image(self):
        if self.image_path:
            self.image = Image.open(self.image_path)
            self.tk_image = ImageTk.PhotoImage(self.image)
            
            # Configure Canvas size and scrolling region
            self.canvas.create_image(0, 0, anchor="nw", image=self.tk_image)
            self.canvas.config(scrollregion=self.canvas.bbox("all"))
            
            # Bind mouse events
            self.canvas.bind("<ButtonPress-1>", self.on_press)
            self.canvas.bind("<B1-Motion>", self.on_drag)
            self.canvas.bind("<ButtonRelease-1>", self.on_release)
            print(f"Loaded image: {self.image_path}")

    def on_press(self, event):
        self.start_x = self.canvas.canvasx(event.x)
        self.start_y = self.canvas.canvasy(event.y)
        self.rect = self.canvas.create_rectangle(self.start_x, self.start_y, event.x, event.y, outline="red")

    def on_drag(self, event):
        cur_x = self.canvas.canvasx(event.x)
        cur_y = self.canvas.canvasy(event.y)
        self.canvas.coords(self.rect, self.start_x, self.start_y, cur_x, cur_y)

    def on_release(self, event):
        end_x = self.canvas.canvasx(event.x)
        end_y = self.canvas.canvasy(event.y)
        self.crop_coords.append((self.start_x, self.start_y, end_x, end_y))

        # Pop-up input for metadata
        meta = simpledialog.askstring("Metadata Input", "Enter metadata for this crop:")
        self.metadata.append({"coords": (self.start_x, self.start_y, end_x, end_y), "meta": meta})

    def save_crops(self):
        crops_info = []
        for idx, coords in enumerate(self.crop_coords):
            cropped_img = self.image.crop(coords)
            crop_filename = os.path.join(self.output_dir, f"crop_{idx+1}.png")
            cropped_img.save(crop_filename)
            crops_info.append({"file": crop_filename, "meta": self.metadata[idx]["meta"]})
        self.example["crops"] = crops_info
        self.root.destroy()  # Close the window

if __name__ == "__main__":
    # Specify the image path and output directory here
    IMAGE_PATH = "/Users/rishabh.maheshwary/Downloads/multilingual_exams/JEE_Adv/2024/imgs/JEEAdv2024_Paper2_Hindi/page_10.png"  # Path to your image
    OUTPUT_DIR = "output_crops"     # Directory to save cropped images and metadata
    
    root = tk.Tk()
    app = ImageCropper(root, IMAGE_PATH, OUTPUT_DIR)
    root.mainloop()
