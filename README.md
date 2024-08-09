<div align="center" markdown>

<img src="xxx"/>

# Annotation Validator

<p align="center">
  <a href="#Overview">Overview</a> •
  <a href="#How-To-Run">How To Run</a>
</p>

</div>

[![](https://img.shields.io/badge/supervisely-ecosystem-brightgreen)](https://ecosystem.supervise.ly/apps/supervisely-ecosystem/annotation-validator)
[![](https://img.shields.io/badge/slack-chat-green.svg?logo=slack)](https://supervise.ly/slack)
![GitHub release (latest SemVer)](https://img.shields.io/github/v/release/supervisely-ecosystem/annotation-validator)
[![views](https://app.supervise.ly/img/badges/views/supervisely-ecosystem/annotation-validator)](https://supervise.ly)
[![runs](https://app.supervise.ly/img/badges/runs/supervisely-ecosystem/annotation-validator)](https://supervise.ly)


## Overview

The Image Annotation Validator is an application designed to validate the correctness of image annotations within a project. This tool iterates through the specified project and associated datasets (including nested datasets), ensuring that each image's annotations meet predefined criteria. The app does not make any changes to the original project, all the changes are being made in a duplicated project.

Application has two modes:

- **Tagging**

The annotation that fail to meet the criteria, will be marked with a tag.

- **Try to Correct Figures**

The application will correct invalid figures if possible, and delete if not.

## How To Run

Step 1: Run the application from the Ecosystem, or from the context menu of a project/dataset


Step 2: In the modal window, you can specify the action to be applied, and the tag name (if tagging mode is selected)

<img src="xxx"/>