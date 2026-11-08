import unittest
from version_maintenance import transform, eligible

class MaintenanceTests(unittest.TestCase):
    def test_original_published_change_example(self):
        raw = b'<VersionPrefix>4.6.1</VersionPrefix>\n<VersionPrefix Condition="x">4.6.2</VersionPrefix>\n<AssemblyVersion>4.0.5.0</AssemblyVersion>\n'
        self.assertEqual(transform(raw, None)[0], b'<VersionPrefix>4.6.2</VersionPrefix>\n<VersionPrefix Condition="x">4.6.3</VersionPrefix>\n<AssemblyVersion>4.0.6.0</AssemblyVersion>\n')
    def test_all_no_increment_lines_protected(self):
        raw = b'<IsPackable>true</IsPackable><!-- NO-INCREMENT -->\n<VersionPrefix>1.2.3</VersionPrefix><!-- NO-INCREMENT -->\n'
        self.assertEqual(transform(raw, None), (raw, []))
    def test_baseline_and_packability(self):
        raw = b'<PackageValidationBaselineVersion>4.6.0</PackageValidationBaselineVersion>\n<IsPackable>true</IsPackable>\n'
        self.assertEqual(transform(raw, '4.6.1')[0], b'<PackageValidationBaselineVersion>4.6.1</PackageValidationBaselineVersion>\n<IsPackable>false</IsPackable>\n')
    def test_bom_crlf_and_missing_final_newline_preserved(self):
        raw = b'\xef\xbb\xbf<VersionPrefix>1.2.3</VersionPrefix>\r\n<Other>x</Other>'
        self.assertEqual(transform(raw, None)[0], b'\xef\xbb\xbf<VersionPrefix>1.2.4</VersionPrefix>\r\n<Other>x</Other>')
    def test_scope_excludes_tests_and_wrong_types(self):
        self.assertTrue(eligible('src/A/Versioning.props'))
        for path in ['src/A/tests/A.csproj', 'eng/A.props', 'src/A/readme.md']:
            self.assertFalse(eligible(path))
    def test_unknown_feed_never_silently_passes(self):
        with self.assertRaises(ValueError):
            transform(b'<PackageValidationBaselineVersion>1.2.3</PackageValidationBaselineVersion>', None)

if __name__ == '__main__':
    unittest.main()
