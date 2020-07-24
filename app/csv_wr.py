import csv
import logging

log = logging.getLogger()


class CSVWrite():
    def write_csv_from_list_of_dicts(
            self, input_listdict, fieldnames, filename):
        """
        Expects a list of dictionaries. Fieldnames must be specified for each
        column. Example input list of dicts:
        [
            {
                "Column1": "Row 1"
                "Column2": "Row 1"
            },
            {
                "Column1": "Row 2"
                "Column2": "Row 2"
            }
        ]

        Will generate the following CSV:
        Column1,Column2
        Row1,Row1
        Row2,Row2
        """
        with open(filename, 'w') as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            for i in input_listdict:
                writer.writerow(i)
        log.info(f"Wrote {filename}")

    def write_csv_from_dict_list(self, input_dict, fieldnames, filename):
        """
        Expects a dictionary of list of dictionaries. Fieldnames must be
        specified for each column. Example input dict of list of dictionaries:
        {
            "Entry1":
                [
                    {
                        "Fieldname2": "Row 1"
                        "Fieldname3": "Row 1"
                    },
                    {
                        "Fieldname2": "Row 2"
                        "Fieldname3": "Row 2"
                    }
                ]

        }

        Will generate the following CSV:
        Fieldname1,Fieldname2,Fieldname3
        Entry1,Row1,Row1
        Entry1,Row2,Row2
        """
        with open(filename, 'w') as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            for entry in input_dict:
                row = input_dict[entry]
                for r in row:
                    r[fieldnames[0]] = entry
                    writer.writerow(r)
        log.info(f"Wrote {filename}")
