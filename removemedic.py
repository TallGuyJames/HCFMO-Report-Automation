import os
import shutil
from pathlib import Path
import xml.etree.ElementTree as ET

def process_incident(xml_file):
    tree = ET.parse(xml_file)
    root = tree.getroot()

    units_parent = root.find('Units')

    if units_parent is not None:
        for unit in units_parent.findall('Unit'):
            radio_number = unit.get('radio_number')
            if radio_number and radio_number.startswith('M'):
                units_parent.remove(unit)

    remaining_units = root.find('Units')
    earliest_time = None
    for unit in remaining_units.findall('Unit'):
        time_arrived = unit.get('time_arrivedatscene')
        if time_arrived:
            if earliest_time is None or time_arrived < earliest_time:
                earliest_time = time_arrived

    # Update Incident.time_first_unit_arrived
#    if earliest_time:
#        incident.set('time_first_unit_arrived', earliest_time)

    # Save the modified XML back to the file
    tree.write(xml_file)


#define paths
current_dir = Path.cwd()
sub_dir = current_dir / 'processed_xml'
sub_dir.mkdir(exist_ok=True)

#process each xml file in the directory
for xml_file in current_dir.glob('*.xml'):
    process_incident(xml_file)
    dest_path = sub_dir / xml_file.name
    shutil.move(xml_file, dest_path)

print("Processing complete. Modified files have been moved to the 'processed_xml' directory.")

