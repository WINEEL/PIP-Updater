def filterpip():
    """Reads the old.txt file, extracts package names, and writes to new.txt"""
    input_file = "datap_/old.txt"
    output_file = "datap_/new.txt"

    try:
        with open(input_file, encoding="utf-8") as f, open(output_file, "w", encoding="utf-8") as g:
            for line in f:
                if "=" in line:
                    package = line.split("=", maxsplit=1)[0].strip()
                    g.write(package + "\n")
        print("Filtered package list saved to new.txt")
    except FileNotFoundError:
        print(f"Error: {input_file} not found!")
