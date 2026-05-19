"""CLI entry point for plan-forge."""
import argparse


def main() -> None:
    """plan-forge CLI dispatcher."""
    parser = argparse.ArgumentParser(prog="plan-forge")
    parser.parse_args()


if __name__ == "__main__":
    main()
