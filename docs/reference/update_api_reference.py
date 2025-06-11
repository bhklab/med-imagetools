"""Script for automatically updating the API reference based on the structure of src/imgtools."""

from pathlib import Path

base_docs_dir = Path("docs/reference")
base_src_dir = Path("src/imgtools")

def crawl_dir(input_dir: Path, output_dir: Path) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)
    pages_in_section = ["..."]
    for f in sorted(input_dir.iterdir()):
        if f.name.startswith(("_", ".")) or f.name in ["datasets", "cli"]:
            continue

        if f.is_dir():
            crawl_dir(f, output_dir / f.name)
            pages_in_section.append(f.name)

        elif f.suffix == ".py":
            # Convert path to module path like: imgtools.submodule.file
            relative_path = f.relative_to(base_src_dir).with_suffix('')
            dotted_path = "imgtools." + ".".join(relative_path.parts)

            # Write API ref markdown file
            output_file = output_dir / f"{f.stem}.md"
            output_file.write_text(f"::: {dotted_path}\n")
    if pages_in_section:
        pages_string = "nav:\n" + "\n".join([f"- {x}" for x in pages_in_section])
        pages_file = output_dir / ".pages"
        pages_file.write_text(pages_string)

if __name__ == "__main__":
    crawl_dir(base_src_dir, base_docs_dir)
