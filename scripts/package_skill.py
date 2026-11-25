#!/usr/bin/env python3
"""Package the reusable skill using the same asset policy as package_showcase."""
from pathlib import Path
import package_showcase

ROOT = Path(__file__).resolve().parents[1]


def runtime_files(root=ROOT):
    return list(package_showcase.skill_files(root))


def package(out, root=ROOT):
    return package_showcase.package(out, root=root)


if __name__ == '__main__':
    package_showcase.main()
