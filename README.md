# Vibrational Natural Frequency Analyzer

**Liberty University Capstone Project, Team 8**

This repository contains software designed by Team 8 from Liberty University as part of a Capstone project. The software is a tool used to analyze and determine vibrational natural frequencies, leveraging the PyQt and PyQtGraph libraries for its graphical user interface and visualizations.

![Vibrational Frequency Analysis](live_data.png)
![Vibrational Frequency Analysis](frequency_analysis.png)

## Table of Contents

- [Project Overview](#project-overview)
- [Features](#features)
- [Installation](#installation)
- [Usage](#usage)
- [Dependencies](#dependencies)
- [File Structure](#file-structure)

---

## Project Overview

The goal of this software is to analyze the vibrational natural frequencies of a system or object. This analysis can be essential for applications in engineering and physics, particularly for understanding resonant behaviors and designing systems that avoid destructive resonance. 

The GUI is built using PyQt and PyQtGraph, providing an interactive, user-friendly interface for input, visualization, and analysis.

## Features

- **Interactive GUI** for data input and control
- **Real-time graphing** of frequency analysis results using PyQtGraph
- **Data visualization tools** for clearer insights into vibrational modes
- **Data export options** for saving results

## Installation

### Prerequisites

Make sure Python 3.7+ is installed on your system.

### Setting Up

1. Clone the repository:
   ```bash
   git clone https://github.com/L0GIC0L/Team_M8_Code.git
   cd Team_M8_Code
   ```

2. Install the required dependencies:
   ```bash
   pip install -r requirements.txt
   ```

> Note: `requirements.txt` should list all libraries required for this project (e.g., `pyqt5`, `pyqtgraph`). 

### Running the Application

After installation, run the application with the following command:
```bash
python main.py
```

## Usage

1. Launch the program using the above command.
2. Use the GUI to input system parameters required for vibrational analysis.
3. Select options to initiate analysis, view frequency plots, and adjust settings as needed.
4. Visualizations of the vibrational frequencies will be displayed in real-time.
5. Save or export your results using the provided options.

## Dependencies

The software relies on the following libraries:

- **PyQt6** - for creating the graphical user interface
- **PyQtGraph** - for plotting and visualizing frequency data
- **NumPy**  - for numerical computations
- **Pandas** - for file logging
- **PGlive** - for live plotting
- **SciPy** - for FFT and data manipulation

Install these using `pip install -r requirements.txt` or individually as shown below:
```bash
pip install pyqt6 pyqtgraph numpy scipy pglive pandas
```

## File Structure

Here's an overview of the primary files and directories in this repository:

- **New_PGLive.py** - Main entry point for the application
- **/Samples/** - Directory containing captured example samples
- **/Preferences/** - Directory for storing stylesheets and settings
- **/Cached_Samples/** - Directory containing random samples cached by the application
- **/Arduino_Scripts/** - Directory containing the utilized arduino scripts
- **/Outdated/** - Directory containing old versions of the application


> You can add specific details on additional files as needed.
