# **Cleaner Data Tickets**

## Introduction

This project automates the cleaning of data files (Excel/CSV) containing natural language fields—such as descriptions, comments, or notes. Driven by a single YAML configuration file, it applies configurable transformations (text normalization, pattern removal, date and type conversions) and quality checks (duplicate handling, allowed values, null filling) to produce clean, consistent datasets ready for analysis.

## Repository Structure

1. [Backend](./backend)
    * [transforms.py](./backend/transforms.py): Definition of all data-cleaning transforms
    * [Dockerfile](./backend/dockerfile): Docker image setup for the cleaner

2. [Config](./config)
    * [config.yaml](./config/config.yaml): YAML file with input/output paths and transform rules

3. [Data](./data)
    * [Source](./data/source) : Raw Excel/CSV files to be cleaned
    * [Source_limpio](./data/source_limpio) : Output folder for cleaned files 
4. [Scripts](./scripts/)
    * [cleaner_2.py](./scripts/cleaner_2.py): Main entrypoint script
    * [cleaner.py](./scripts/cleaner.py): Initial data cleaning script
    * [conteo_tokens.py](./scripts/conteo_tokens.py): Token-counting and cost summary script
5. [tests](./tests)
    * [test_transforms.py](./tests/test_transforms.py):  Test suite
6. Root  Directory
    * [README](README.md): Project overview and usage instructions
    * [requirements.txt](requirements.txt): Python libraries and dependencies
    * [.dockerignore](.dockerignore): Files/folders excluded when building Docker image
    * [.gitignore](.gitignore): Files/folder excluded from Git commits
    * [pytest](pytest): Pytest configuration

## Usage and Development

* Docker installed 

To begin working with this repository, follow these steps:

1. **Clone the repository**
```bash
git clone https://github.com/Andres-Cortes-Axity/cleaner_data_tickets.git

cd cleaner_data_tickets
```
2. **Configuration**
you need to adjust the application settings in the config file.
1. **Open the configuration at `config/config.yaml`:**
With the following lines in the YAML you can configure:
    * **input_files** :  List of file paths or directories to scan for raw ticket files. The cleaner will process any `.xlsx`, `.xls` or `.csv` it finds under each path.
    ```yaml
    # List of input files or directories to process (accepts .xlsx, .xls, .csv)
    input_files:
    - "./data/source/"
    ```
    * **output**: option to define the path where cleaned files will be saved and the output format.
    ```yaml
    # Output settings: directory and format for cleaned files
    output:
    dir: "./data/source_limpio/"
    format: "xlsx"
    ```
    * **schema**: defines the expected data type for each field in your dataset (e.g. `string`, `int`, `datetime`). The cleaner uses these definitions to cast values correctly, validate incoming data, and surface any type mismatches before writing the output.
    ```yaml
    # Schema definitions: expected data types for each field
    schema:
        mesa_de_ayuda: string       # Name of help desk or support queue
        nivel: int                  # Ticket priority level or severity
        prioridad: string           # Ticket priority as text
        origen: string              # Source system or reporting channel
        estado: string              # Ticket status
        tipo: string                # Ticket type or classification
        fecha_creacion: datetime    # Creation timestamp of the ticket
        fecha_cierre: datetime      # Closing timestamp of the ticket
        asunto: string              # Subject or summary of the ticket
        fecha_solucion: datetime    # Resolution timestamp
        id: string                  # Unique identifier for each ticket
        categoria_principal: string # Main category of the ticket
        subcategoria: string        # Subcategory of the ticket
        accion: string              # Action or next steps extracted from category
    ```
    * **mappings**:This mappings section defines how each field in the cleaned dataset is derived from the raw file: for every field, `source` specifies the exact column header in the input and `transforms` is an ordered list of operations (e.g. `normalize_text`, `regex_extract`, `to_datetime`, `remove_pattern`) applied immediately after reading the raw value to standardize text, extract or remove patterns, convert formats (dates, numbers) and ensure each value matches its intended type before any validation or output.
    ```yaml
    mappings:
        mesa_de_ayuda:
            source: "Mesa de ayuda" # Column name in source file
            transforms:
            - { name: "normalize_text", lowercase: true, strip_accents: true, trim: true }
            - { name: "remove_pattern", pattern: "nivel\\s*\\d+" }
        nivel:
            source: "Mesa de ayuda"
            transforms:
            - { name: "regex_extract", pattern: "nivel\\s*(\\d+)", group: 1, as_type: int }
        prioridad:
            source: "Prioridad"
            transforms:
            - { name: "normalize_text", lowercase: true, strip_accents: true, trim: true }
        origen:
            source: "Origen"
            transforms:
            - { name: "normalize_text", lowercase: true, strip_accents: true, trim: true }
        estado:
            source: "Estado"
            transforms:
            - { name: "normalize_text", lowercase: true, strip_accents: true, trim: true }
    ```
    * **quality**: This quality section configures validation rules for your cleaned data: the `duplicates` block uses `key` to identify duplicate rows, `action` to decide whether to drop or keep the latest entry, and `latest_by` to pick which record is considered most recent; `allowed_values` lists permitted entries for specific fields to catch invalid data early; and `null_handling` determines whether to explicitly fill missing values with `null` to avoid silent data loss.  
    ```yaml
    # Quality checks configuration: duplicates and allowed values
    quality:
    duplicates:
        key: "id"     # Column to identify duplicate rows
        action: "keep_latest" # Action to take (e.g., drop or keep latest)
        latest_by: "fecha_creacion"   # Column to determine which record is latest
    allowed_values:
        estado: ["abierto", "cerrado", "en espera", "otro"] # Permitted status values
    null_handling:
        fill_with_null: true    # Whether to explicitly fill missing values with null
    ```
3. **Build the Docker image** 
```bash
docker build -f backend/Dockerfile -t cleaner_data_tickets:latest .
```

4. **Run Data Cleaner**
```bash
docker run --rm -v "C:/Users/Pedro.Espinosa/Documents/Arquetipos/cleaner_data_tickets/data":/app/data cleaner_data_tickets:latest
```
**Note: Adjust the output path to whichever directory you want your cleaned dataset to be saved in. Once you’ve set the path, remove the quotation marks so the command is clean.**


## Credits 

People who have contributed to the solution.

  - **Andres Cortes Gonzalez**
  - **Berenice Zavala Jiménez**
  - **Pedro Daniel Espinosa Nava**
  - **David Alexander Dorado Lezama**

## License

**Specify the license under which the solution is distributed and any other relevant legal information.**

## Contact

  - **Andres Cortes Gonzalez         Andres.CortesG@axity.com**
  - **Berenice Zavala Jiménez    Berenice.Zavala@axity.com**
  - **Pedro Daniel Espinosa Nava      Pedro.Espinosa@axity.com**
  - **David Alexander Dorado Lezama      David.Dorado@axity.com**
    


##

<br>

![image](https://github.com/user-attachments/assets/2a29f6f3-a512-458b-a223-bf0484f9bcc3)

<br>

### This ART is part of Axity's CReA, for more information visit [CReA]
*[CReA - Inicio (sharepoint.com)](https://intellego365.sharepoint.com/sites/CentralAxity/Corporativo/CReA/SitePages/Home.aspx?xsdata=MDV8MDJ8fGUwYzYzYzgwOGNmZjRjMzIyY2JhMDhkY2UxNjg5ZmU0fDAwYTA1Y2UwYmQzZDQyMTVhNTY5YzYyNjFhMjBhMzllfDB8MHw2Mzg2MzMwODY2NTUxNDcxOTR8VW5rbm93bnxWR1ZoYlhOVFpXTjFjbWwwZVZObGNuWnBZMlY4ZXlKV0lqb2lNQzR3TGpBd01EQWlMQ0pRSWpvaVYybHVNeklpTENKQlRpSTZJazkwYUdWeUlpd2lWMVFpT2pFeGZRPT18MXxMMk5vWVhSekx6RTVPbTFsWlhScGJtZGZUVWRGZWsweVdtbE5hbGwwV2tkS2FFNURNREJOTWxGNlRGUm5kMXBYU1hSTk1rbDNUMVJqZDFsdFVtaE5iVlpxUUhSb2NtVmhaQzUyTWk5dFpYTnpZV2RsY3k4eE56STNOekV4T0RZME56UTB8N2YzMGEyNjYxOTIzNGJkYTJjYmEwOGRjZTE2ODlmZTR8NjE3Y2VhMTRlZDA3NDY3ZGI1OWQxNDdjNGQ0OWY2NGI%3D&sdata=Yk5iaWpjWkoycW13ODdENUI1b05nNTFyRzI2bnlBUkJOZ1RCM0tYUU1QVT0%3D&ovuser=00a05ce0-bd3d-4215-a569-c6261a20a39e%2CPedro.Espinosa%40axity.com&OR=Teams-HL&CT=1727714402558&clickparams=eyJBcHBOYW1lIjoiVGVhbXMtRGVza3RvcCIsIkFwcFZlcnNpb24iOiI0OS8yNDA4MTcwMDQyMSIsIkhhc0ZlZGVyYXRlZFVzZXIiOmZhbHNlfQ%3D%3D)*
