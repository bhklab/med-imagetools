# from imgtools.io.writers.abstract_base_writer import (
#     ExampleWriter,
#     ExistingFileMode,
# )

# if __name__ == "__main__":
#     import random
#     from datetime import datetime
#     from pathlib import Path

#     from pathos.multiprocessing import ProcessingPool as Pool  # type: ignore
#     from tqdm import tqdm
#     from tqdm.contrib.concurrent import process_map

#     from imgtools.loggers import tqdm_logging_redirect

#     # Single shared writer (dill-serializable)
#     shared_writer = ExampleWriter(
#         root_directory=Path("temp_outputs/example_writer"),
#         filename_format="{subject_id}/{modality}/{filename}",
#         existing_file_mode=ExistingFileMode.OVERWRITE,
#         create_dirs=True,
#     )

#     def generate_context(i: int) -> dict[str, str | float]:
#         return {
#             "subject_id": f"subject_{i % 10}",
#             "modality": random.choice(["CT", "MR", "SEG"]),
#             "filename": f"fake_file_{i}.txt",
#             "quality_score": round(random.uniform(0.0, 1.0), 3),
#             "timestamp": datetime.now().isoformat(timespec="seconds"),
#         }

#     def write_with_shared_writer(args) -> None:
#         writer, i = args
#         ctx = generate_context(i)
#         writer.save(f"Shared writer content {i}", **ctx)

#     # wrap in lambda to capture both writer and index
#     N = 1000

#     tuples = [(shared_writer, i) for i in range(N)]

#     with tqdm_logging_redirect():
#         results = process_map(
#             write_with_shared_writer,
#             tuples,
#             max_workers=8,
#             desc="Writing files",
#             total=N,
#         )

#     print(
#         f"✔ Done writing 1000 files to: {shared_writer.root_directory.resolve()}"
#     )
#     print(f"✔ Index: {shared_writer.index_file.resolve()}")
