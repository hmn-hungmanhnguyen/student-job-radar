from pathlib import Path
import subprocess
import sys


ROOT_DIR = Path(__file__).resolve().parent.parent
SRC_DIR = ROOT_DIR / "src"


PIPELINE_STEPS = [
    "download_pdfs.py",
    "extract_pdf_text.py",
    "parse_jobs.py",
    "export_excel.py",
]


def run_script(script_name: str) -> None:
    script_path = SRC_DIR / script_name

    print("=" * 80)
    print(f"Running: {script_name}")
    print("=" * 80)

    subprocess.run(
        [sys.executable, str(script_path)],
        cwd=ROOT_DIR,
        check=True,
    )


def main() -> None:
    print("Starting Student Job Radar pipeline...")

    for script in PIPELINE_STEPS:
        run_script(script)

    print("=" * 80)
    print("Pipeline completed successfully.")
    print("Output files:")
    print("- data/jobs.csv")
    print("- data/jobs.xlsx")
    print("=" * 80)


if __name__ == "__main__":
    main()