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

    parser.add_argument("--visualize", type=bool, default=False,
                        help="Whether to visualize the data graph")

    parser.add_argument("--spacing", nargs=3, type=float, default=(1., 1., 0.),
                        help="The resampled voxel spacing in  (x, y, z) directions.")

    parser.add_argument("--n_jobs", type=int, default=-1,
                        help="The number of parallel processes to use.")

    parser.add_argument("--show_progress", action="store_true",
                        help="Whether to print progress to standard output.")
    
    parser.add_argument("--nnunet", default=False, action="store_true",
                        help="Whether to make the output conform to nnunet requirements.")

    parser.add_argument("--train_size", type=float, default=1.0,
                        help="The proportion of data to be used for training, as a decimal.")

    parser.add_argument("--random_state", type=int, default=42,
                        help="The random state to be used for the train-test-split.")

    return parser.parse_known_args()[0]