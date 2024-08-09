<div align="center" markdown>

<img src="https://github.com/user-attachments/assets/758eb893-bc1c-4ff5-aa06-286b18557cae"/>

# Annotation Validator

<p align="center">
  <a href="#Overview">Overview</a> •
  <a href="#How-To-Run">How To Run</a>
</p>

[![](https://img.shields.io/badge/supervisely-ecosystem-brightgreen)](https://ecosystem.supervise.ly/apps/supervisely-ecosystem/annotation-validator)
[![](https://img.shields.io/badge/slack-chat-green.svg?logo=slack)](https://supervise.ly/slack)
![GitHub release (latest SemVer)](https://img.shields.io/github/v/release/supervisely-ecosystem/annotation-validator)
[![views](https://app.supervise.ly/img/badges/views/supervisely-ecosystem/annotation-validator)](https://supervise.ly)
[![runs](https://app.supervise.ly/img/badges/runs/supervisely-ecosystem/annotation-validator)](https://supervise.ly)

</div>



## Overview

The Image Annotation Validator is an application designed to validate the correctness of image annotations within a project. This tool iterates through the specified project and associated datasets (including nested datasets), ensuring that each image's annotations meet predefined criteria. The app does not make any changes to the original project, all the changes are being made in a duplicated project.

Application has two modes:

- **Tagging**: The annotation that fail to meet the criteria, will be marked with a tag.

- **Autocorrect**: The application will correct invalid figures if possible.

## How To Run

Step 1: Run the application from the Ecosystem, or from the context menu of a project/dataset

Step 2: Specify the action to be applied to invalid annotation objects

<img src="https://github.com/user-attachments/assets/206838da-a761-4728-9b2d-c6c41c9965b7"/>