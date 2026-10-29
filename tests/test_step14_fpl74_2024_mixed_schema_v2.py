import csv,io,unittest
from scripts.step14_fpl74_2024_mixed_schema_xg_corrected_v2 import (
    normalize_csv,MixedFPLSchemaError)

def sample_rows():
    h=[f"unused_{i}" for i in range(42)]
    for i,name in ((14,"fixture"),(19,"kickoff_time"),(21,"modified"),
                   (22,"opponent_team"),(39,"was_home"),(41,"GW")):h[i]=name
    r=["0"]*42
    for i,v in ((14,"218"),(19,"2025-01-18T12:30:00Z"),(21,"False"),
                (22,"15"),(39,"False"),(41,"22")):r[i]=v
    return h,r

def csvbytes(header,rows):
    io_=io.StringIO(newline="")
    writer=csv.writer(io_)
    writer.writerow(header)
    writer.writerows(rows)
    return io_.getvalue().encode()

class OldPlayerXG42to49SchemaTests(unittest.TestCase):
    def test_7_new_GW22_columns_are_removed_without_modifying_xg_fields(self):
        h,r=sample_rows()
        row49=r[:21]+["1","0","1","0","0","0","0"]+r[21:]
        normalized,proof=normalize_csv(csvbytes(h,[r,row49]))
        parsed=list(csv.DictReader(io.StringIO(normalized.decode())))
        self.assertEqual(len(parsed),2)
        self.assertEqual(parsed[0]["fixture"],"218")
        self.assertEqual(parsed[1]["fixture"],"218")
        self.assertEqual(parsed[1]["was_home"],"False")
        self.assertEqual(parsed[1]["opponent_team"],"15")
        self.assertEqual(parsed[1]["GW"],"22")
        self.assertEqual(proof["corrected_GW22_plus_49_column_rows"],1)
        self.assertEqual(proof["unchanged_42_column_rows"],1)
        self.assertNotEqual(proof["original_old_file_sha256"],
                            proof["normalized_in_memory_sha256"])
    def test_do_not_guess_non_numeric_extra_columns_or_future_gw(self):
        h,r=sample_rows()
        for bad in (r[:21]+["NaN"]+["0"]*6+r[21:],
                    r[:21]+["0"]*7+r[21:41]+["5"]):
            with self.assertRaises(MixedFPLSchemaError):
                normalize_csv(csvbytes(h,[bad]))
    def test_original_was_home_side_must_be_bool(self):
        h,r=sample_rows();r[39]="2"
        with self.assertRaises(MixedFPLSchemaError):
            normalize_csv(csvbytes(h,[r]))

if __name__=="__main__":
    unittest.main()
