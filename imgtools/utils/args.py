from argparse import ArgumentParser

def parser():
    parser = ArgumentParser("imgtools Automatic Processing Pipeline.")

    #arguments
    parser.add_argument("input_directory", type=str,
                        help="Path to top-level directory of dataset.")

    parser.add_argument("output_directory", type=str,
                        help="Path to output directory to save processed images.")

    parser.add_argument("--modalities", type=str, default="CT",
                        help="List of desired modalities. Type as string for ex: RTSTRUCT,CT,RTDOSE")

    parser.add_argument("--visualize", default=False, action="store_true",
                        help="Whether to visualize the data graph")

    parser.add_argument("--spacing", nargs=3, type=float, default=(1., 1., 0.),
                        help="The resampled voxel spacing in  (x, y, z) directions.")

    parser.add_argument("--n_jobs", type=int, default=-1,
                        help="The number of parallel processes to use.")

    parser.add_argument("--show_progress", action="store_true",
                        help="Whether to print progress to standard output.")

    parser.add_argument("--warn_on_error", default=False, action="store_true",
                        help="Whether to warn on error.")

    parser.add_argument("--overwrite", default=False, action="store_true",
                        help="Whether to write output files even if existing output files exist.")
    
    parser.add_argument("--nnunet", default=False, action="store_true",
                        help="Whether to make the output conform to nnunet requirements.")

    parser.add_argument("--train_size", type=float, default=1.0,
                        help="The proportion of data to be used for training, as a decimal.")

    parser.add_argument("--random_state", type=int, default=42,
                        help="The random state to be used for the train-test-split.")

    parser.add_argument("--read_yaml_label_names", default=False, action="store_true",
                        help="Whether to read the label names from roi_names.yaml in the input directory.")

    parser.add_argument("--ignore_missing_regex", default=False, action="store_true",
                        help="Whether to ignore patients with no ROI regexes that match the given ones. Will throw an error on patients without matches if this is not set.")

    parser.add_argument("--roi_yaml_path", type=str, default="",
                        help="Path to the YAML file defining ROI regexes")

    parser.add_argument("--custom_train_test_split", default=False, action="store_true",
                        help="Whether to use a custom train-test-split, stored in custom_train_test_split.yaml in the input directory.")

    parser.add_argument("--nnunet_inference", default=False, action="store_true",
                        help="Whether to generate data for nnUNet inference.")
    
    parser.add_argument("--dataset_json_path", type=str, default="",
                        help="Path to the dataset.json file defining image modality indices for nnUNet inference.")

    parser.add_argument("--continue_processing", default=False, action="store_true",
                        help="Whether to continue processing a partially completed dataset.")
    
    parser.add_argument("--dry_run", default=False, action="store_true",
                        help="Make a dry run of the pipeline, only producing the edge table and dataset.csv.")

    parser.add_argument("--verbose", default=False, action="store_true",
                        help="Verbose output flag.")

    parser.add_argument("--update", default=False, action="store_true",
                        help="Update crawled index. In other words, process from scratch.")

    parser.add_argument("--roi_select_first", default=False, action="store_true",
                        help="Only select first matching regex/ROI name.")

    parser.add_argument("--roi_separate", default=False, action="store_true",
                        help="Process each matching regex/ROI into separate masks. Each matched mask will be saved as ROI_n. (n = index from list of regex/ROIs)")

    # parser.add_argument("--custom_train_test_split_path", type=str,
    #                     help="Path to the YAML file defining the custom train-test-split.")

    return parser.parse_known_args()[0]