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

The Image Annotation Validator is an application designed to autocorrect the invalid image annotations within a project. This tool iterates through the specified project and associated datasets (including nested datasets), ensuring that each image's annotations meet predefined criteria. The app does not make any changes to the original project, all the changes are being made in a duplicated project. 

The app also tags the annotation objects and the image which contains them with a tag. This functionality can be toggled in the modal window.

## How To Run

Run the application from the Ecosystem, or from the context menu of a project/dataset

<img src="https://github.com/user-attachments/assets/d49498b1-264b-45dd-aaac-8de9fd5e8681"/>