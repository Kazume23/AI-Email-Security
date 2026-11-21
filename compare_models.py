import argparse
import subprocess
import sys

from ai_email_security.experiments import run_experiment


def main():
    parser = argparse.ArgumentParser(
        description="Porównanie modeli bez treningu i strojenia progów."
    )
    parser.add_argument("--manifest", required=True)
    parser.add_argument(
        "--dataset-kind", choices=["demonstration", "independent"], required=True
    )
    parser.add_argument("--limit", type=int, default=10)
    args = parser.parse_args()
    print(run_experiment(args.manifest, args.dataset_kind, args.limit))


if __name__ == "__main__":
    if not sys.flags.utf8_mode:
        raise SystemExit(
            subprocess.call([sys.executable, "-X", "utf8", __file__, *sys.argv[1:]])
        )
    main()
