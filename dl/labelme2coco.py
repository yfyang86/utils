import json
import base64
from PIL import Image
import io
import os
from concurrent.futures import ThreadPoolExecutor

global_image_save_dir = ''
global_coco_save_path = ''


#@description: Convert labelme json to COCO format
class LabelMeToCOCOConverter:
    def __init__(self, labelme_dir, image_save_dir, coco_save_path):
        self.labelme_dir = labelme_dir
        self.image_save_dir = image_save_dir
        self.coco_save_path = coco_save_path
        self.coco_data = {
            "info": {},
            "licenses": [],
            "images": [],
            "annotations": [],
            "categories": []
        }
        self.category_id_map = {}
        self.image_id = 1
        self.annotation_id = 1

    def convert_all(self):
        # Iterate over all LabelMe JSON files in the specified directory
        for filename in os.listdir(self.labelme_dir):
            if filename.endswith('.json'):
                labelme_json_path = os.path.join(self.labelme_dir, filename)
                self.convert_single_file(labelme_json_path)

        # Save the final COCO formatted JSON
        self.save_coco_json()

    # Update the LabelMeToCOCOConverter class to include convert_single_file method
    # !!! Important Assumptiopns:
    # we abandon the threading lock and use the json file name as the image ID,
    # DO notice that, we assume the json file unames are unique
    def convert_single_file(self, labelme_json_path):
        # Use file name without the extension as the image_id
        file_name_without_extension = os.path.splitext(os.path.basename(labelme_json_path))[0]
        # If you are sure that the file name can be an integer, convert it.
        try:
            self.image_id = int(file_name_without_extension)
        except ValueError:
            # If the file name is not an integer, use a hash to ensure a unique identifier
            self.image_id = hash(file_name_without_extension)
        
        self.load_labelme_json(labelme_json_path)
        file_name, image_size = self.decode_and_save_base64_image(file_name=labelme_json_path)
        self.add_image_info(file_name, image_size)
        self.add_annotations()
        # No need to increment self.image_id since it is now unique per file

    def load_labelme_json(self, json_path):
        with open(json_path, 'r') as file:
            self.labelme_data = json.load(file)

    def decode_and_save_base64_image(self, file_name):
        base64_string = self.labelme_data['imageData']
        image_data = base64.b64decode(base64_string)
        image = Image.open(io.BytesIO(image_data))
        image_filename = os.path.basename(file_name).replace('.json', '.png')
        image_save_path = os.path.join(self.image_save_dir, image_filename)
        image.save(image_save_path, 'PNG')
        return image_filename, image.size

    def add_image_info(self, file_name, image_size):
        image_info = {
            "id": self.image_id,
            "width": image_size[0],
            "height": image_size[1],
            "file_name": file_name,
        }
        self.coco_data['images'].append(image_info)

    def add_annotations(self):
        for shape in self.labelme_data['shapes']:
            category_name = shape['label']
            if category_name not in self.category_id_map:
                new_id = len(self.category_id_map) + 1
                self.category_id_map[category_name] = new_id
                self.coco_data['categories'].append({
                    "id": new_id,
                    "name": category_name,
                    "supercategory": "none",
                })
            points = shape['points']
            x_min = min([point[0] for point in points])
            y_min = min([point[1] for point in points])
            x_max = max([point[0] for point in points])
            y_max = max([point[1] for point in points])
            bbox = [x_min, y_min, x_max - x_min, y_max - y_min]
            segmentation = [list(sum(points, []))]

            annotation_info = {
                "id": self.annotation_id,
                "image_id": self.image_id,
                "category_id": self.category_id_map[category_name],
                "bbox": bbox,
                "segmentation": segmentation,
                "area": bbox[2] * bbox[3],  # width * height
                "iscrowd": 0
            }
            self.coco_data['annotations'].append(annotation_info)
            self.annotation_id += 1

    def save_coco_json(self):
        with open(self.coco_save_path, 'w') as json_file:
            json.dump(self.coco_data, json_file)

#'@description: This script is used to parse the labelme json file and convert it to COCO format.
class BatchLabelMeToCOCOConverter:
    def __init__(self, labelme_dir, image_save_dir, coco_save_path):
        self.labelme_dir = labelme_dir
        self.image_save_dir = image_save_dir
        self.coco_save_path = coco_save_path
        self.converter = LabelMeToCOCOConverter(labelme_dir, image_save_dir, coco_save_path)

    def convert_all(self):
        for file_name in os.listdir(self.labelme_dir):
            if file_name.lower().endswith('.json'):
                labelme_json_path = os.path.join(self.labelme_dir, file_name)
                self.converter.convert_single_file(labelme_json_path)

        self.converter.save_coco_json()

def convert_file_threaded(converter, labelme_json_path):
    converter.convert_single_file(labelme_json_path)
    return converter

#@description: Combine the COCO data from all threads into one COCO file
def combine_coco_data(converters, coco_save_path):
    coco_data = {
        "info": {},
        "licenses": [],
        "images": [],
        "annotations": [],
        "categories": []
    }
    category_id_map = {}
    annotation_id = 1

    for converter in converters:
        for image_info in converter.coco_data['images']:
            coco_data['images'].append(image_info)

        for annotation in converter.coco_data['annotations']:
            annotation['id'] = annotation_id
            annotation_id += 1
            coco_data['annotations'].append(annotation)

        for category in converter.coco_data['categories']:
            if category['name'] not in category_id_map:
                category_id_map[category['name']] = category['id']
                coco_data['categories'].append(category)

    with open(coco_save_path, 'w') as json_file:
        json.dump(coco_data, json_file)

#@description: Convert labelme json to COCO format using multi-threading
def covert_thread_main(labelme_dir, image_save_dir, coco_save_path):
    all_files = os.listdir(labelme_dir)
    json_files = [f for f in all_files if f.lower().endswith('.json')]
    
    # Create the image save directory if it doesn't exist
    if not os.path.exists(image_save_dir):
        os.makedirs(image_save_dir)
    
    converters = []
    with ThreadPoolExecutor() as executor:
        # Convert all the LabelMe JSON files using multi-threading
        futures = [executor.submit(convert_file_threaded, LabelMeToCOCOConverter(labelme_dir, image_save_dir=image_save_dir, coco_save_path=coco_save_path), 
                                   os.path.join(labelme_dir, json_file)) for json_file in json_files]
        
        # Wait for all threads to complete
        for future in futures:
            result = future.result()
            converters.append(result)
            print(f"Processed {result}")

    # After all threads are done, combine the data into one COCO file
    combine_coco_data(converters, coco_save_path)


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description='Convert labelme json to COCO format')
    parser.add_argument('--labelme_json_dir', type=str, default= '', help='Path to labelme json file')
    parser.add_argument('--image_save_dir', type=str, default= '', help='Path to save images')
    parser.add_argument('--coco_save_path', type=str, default= '', help='Path to save coco json file')
    parser.add_argument('--threaded', type=bool, default= False, help='Use multi-threading to convert labelme json files')
    args = parser.parse_args()
    
    root_dir =  "./figures/" 

    labelme_dir = args.labelme_json_dir if args.labelme_json_dir != '' else root_dir + 'fig201-400/201-400json/' 
    image_save_dir =  args.image_save_dir if args.image_save_dir != '' else root_dir + 'fig201-400/201-400fig/'
    coco_save_path = args.coco_save_path if args.coco_save_path != '' else root_dir + 'coco/coco_201-400.json'
    
    global_image_save_dir = image_save_dir
    global_coco_save_path = coco_save_path

    # Ensure the image save directory exists
    if not os.path.exists(image_save_dir):
        os.makedirs(image_save_dir)
    
    if not args.threaded:
        batch_converter = BatchLabelMeToCOCOConverter(labelme_dir, image_save_dir, coco_save_path)
        batch_converter.convert_all()
    else:
        covert_thread_main(labelme_dir, image_save_dir, coco_save_path)

