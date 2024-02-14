# utils
Util functions


## labelme2coco

Figure ETL: [coco-etl-code](./dl/labelme2coco.md) extracts all the base64 figures and annotations from the Labelme software to the standard CoCo format. 

- [x] [./dl/labelme2coco.py]: Convert labelme json to COCO format


```
root_dir
  |
  |-- [SRC] transf_coco.py
  |         
  |-- [DIR] coco
  |         |
  |         |-- [OUT_FILE] coco.json: <outputs> COCO json results </outputs>
  |         
  |-- [DIR] figures
  |         |
  |         |-- [OUT_FILE]fig: <outputs> extracted figures </outputs>
  |         |-- [IN_FILE]json: <inputs> seperated annotated json results by Labelme </inputs>
```

Init prompt:

> The process of converting annotations from LabelMe JSON format with base64 encoded images to COCO format involves a few steps. The COCO (Common Objects in Context) format is a standard for object detection, segmentation, and captioning tasks. It's a bit involved, so let's break it down step by step.

