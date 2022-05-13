from imgtools.autopipeline import AutoPipeline

if __name__ == "__main__":
    pipeline = AutoPipeline(input_directory="C:/Users/qukev/BHKLAB/dataset/manifest-1598890146597/NSCLC-Radiomics-Interobserver1",
                            output_directory="C:/Users/qukev/BHKLAB/autopipelineoutput",
                            visualize=True)

    print(f'starting Pipeline...')
    pipeline.run()


    print(f'finished Pipeline!')