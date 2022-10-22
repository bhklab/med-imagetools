conda activate med-imagetools

autopipeline \
    INPUT_DIR \
    OUTPUT_DIR \
    --modalities CT,RTSTRUCT \
    --roi_yaml_path use_case_3_regex.yaml