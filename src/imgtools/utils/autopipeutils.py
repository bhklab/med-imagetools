import glob
import os
import shutil
import pathlib
import pickle    
from .nnunet import generate_dataset_json, markdown_report_images


def save_data(self):
    """
    Saves metadata about processing. 
    """
    files = glob.glob(pathlib.Path(self.output_directory, ".temp", "*.pkl").as_posix())
    for file in files:
        filename = pathlib.Path(file).name
        if filename == "init_parameters.pkl":
            continue
        subject_id = os.path.splitext(filename)[0]
        with open(file,"rb") as f:
            metadata = pickle.load(f)
        self.output_df.loc[subject_id, list(metadata.keys())] = list(metadata.values())  # subject id targets the rows with that subject id and it is reassigning all the metadata values by key
        
    folder_renames = {}
    for col in self.output_df.columns:
        if col.startswith("folder"):
            self.output_df[col] = self.output_df[col].apply(lambda x: x if not isinstance(x, str) else pathlib.Path(x).as_posix().split(self.input_directory)[1][1:]) # rel path, exclude the slash at the beginning
            folder_renames[col] = f"input_{col}"
    self.output_df.rename(columns=folder_renames, inplace=True)  # append input_ to the column name
    self.output_df.to_csv(self.output_df_path)  # dataset.csv

    shutil.rmtree(pathlib.Path(self.output_directory, ".temp").as_posix())

    # Save dataset json
    if self.is_nnunet:  # dataset.json for nnunet and .sh file to run to process it
        imagests_path = pathlib.Path(self.output_directory, "imagesTs").as_posix()
        images_test_location = imagests_path if os.path.exists(imagests_path) else None
        # print(self.existing_roi_names)
        generate_dataset_json(pathlib.Path(self.output_directory, "dataset.json").as_posix(),
                              pathlib.Path(self.output_directory, "imagesTr").as_posix(),
                              images_test_location,
                              tuple(self.nnunet_info["modalities"].keys()),
                              {v: k for k, v in self.existing_roi_names.items()},
                              os.path.split(self.input_directory)[1])
        _, child = os.path.split(self.output_directory)
        shell_path = pathlib.Path(self.output_directory, child.split("_")[1]+".sh").as_posix()
        if os.path.exists(shell_path):
            os.remove(shell_path)
        with open(shell_path, "w", newline="\n") as f:
            output = "#!/bin/bash\n"
            output += "set -e"
            output += f'export nnUNet_raw_data_base="{self.base_output_directory}/nnUNet_raw_data_base"\n'
            output += f'export nnUNet_preprocessed="{self.base_output_directory}/nnUNet_preprocessed"\n'
            output += f'export RESULTS_FOLDER="{self.base_output_directory}/nnUNet_trained_models"\n\n'
            output += f'nnUNet_plan_and_preprocess -t {self.task_id} --verify_dataset_integrity\n\n'
            output += 'for (( i=0; i<5; i++ ))\n'
            output += 'do\n'
            output += f'    nnUNet_train 3d_fullres nnUNetTrainerV2 {os.path.split(self.output_directory)[1]} $i --npz\n'
            output += 'done'
            f.write(output)
        markdown_report_images(self.output_directory, self.total_modality_counter)  # images saved to the output directory
    
    # Save summary info (factor into different file)
    markdown_path = pathlib.Path(self.output_directory, "report.md").as_posix()
    with open(markdown_path, "w", newline="\n") as f:
        output = "# Dataset Report\n\n"
        if not self.is_nnunet:
            output += "## Patients with broken DICOM references\n\n"
            output += "<details>\n"
            output += "\t<summary>Click to see the list of patients with broken DICOM references</summary>\n\n\t"
            formatted_list = "\n\t".join(self.broken_patients)
            output += f"{formatted_list}\n"
            output += "</details>\n\n"

        if self.is_nnunet:
            output += "## Train Test Split\n\n"
            # pie_path = pathlib.Path(self.output_directory, "markdown_images", "nnunet_train_test_pie.png").as_posix()
            pie_path = pathlib.Path("markdown_images", "nnunet_train_test_pie.png").as_posix()
            output += f"![Pie Chart of Train Test Split]({pie_path})\n\n"
            output += "## Image Modality Distribution\n\n"
            # bar_path = pathlib.Path(self.output_directory, "markdown_images", "nnunet_modality_count.png").as_posix()
            bar_path = pathlib.Path("markdown_images", "nnunet_modality_count.png").as_posix()
            output += f"![Pie Chart of Image Modality Distribution]({bar_path})\n\n"
        f.write(output)

    return f
