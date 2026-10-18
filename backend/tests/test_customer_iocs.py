import unittest
import sys
import os

# Ensure backend root is in sys.path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.api.v1.customer_api import get_iocs_feed, _clean_and_classify_ioc
from app.db.mongodb import store


class TestCustomerIOCs(unittest.IsolatedAsyncioTestCase):
    """Test suite covering valid indicators, invalid matches, deduplication, filtering, and empty results."""

    async def asyncSetUp(self):
        store.messages.clear()
        if hasattr(store, "threat_intel"):
            store.threat_intel.clear()

    async def test_01_classify_and_clean_indicators(self):
        """Verify classification of valid IOCs and rejection of invalid matches."""
        # 1. Valid Indicators
        self.assertEqual(_clean_and_classify_ioc("CVE-2024-38077"), ("cve", "CVE-2024-38077"))
        self.assertEqual(_clean_and_classify_ioc("cve-2023-1234"), ("cve", "CVE-2023-1234"))
        self.assertEqual(_clean_and_classify_ioc("192.168.1.100"), ("ip", "192.168.1.100"))
        self.assertEqual(_clean_and_classify_ioc("185.220.101.5"), ("ip", "185.220.101.5"))
        self.assertEqual(_clean_and_classify_ioc("darkmarket777.onion"), ("domain", "darkmarket777.onion"))
        self.assertEqual(_clean_and_classify_ioc("threat-feed.xyz"), ("domain", "threat-feed.xyz"))
        self.assertEqual(
            _clean_and_classify_ioc("e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"),
            ("hash", "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855")
        )
        self.assertEqual(
            _clean_and_classify_ioc("d41d8cd98f00b204e9800998ecf8427e"),
            ("hash", "d41d8cd98f00b204e9800998ecf8427e")
        )
        self.assertEqual(
            _clean_and_classify_ioc("bc1qar0srrr7xfkvy5l643lydnw9re59gtzzwf5mdq"),
            ("wallet", "bc1qar0srrr7xfkvy5l643lydnw9re59gtzzwf5mdq")
        )
        self.assertEqual(
            _clean_and_classify_ioc("0x71C7656EC7ab88b098defB751B7401B5f6d8976F"),
            ("wallet", "0x71C7656EC7ab88b098defB751B7401B5f6d8976F")
        )
        self.assertEqual(_clean_and_classify_ioc("attacker@protonmail.com"), ("email", "attacker@protonmail.com"))

        # 2. Invalid Matches (Must be safely rejected)
        self.assertIsNone(_clean_and_classify_ioc("999.999.999.999")[0])
        self.assertIsNone(_clean_and_classify_ioc("0.0.0.0")[0])
        self.assertIsNone(_clean_and_classify_ioc("255.255.255.255")[0])
        self.assertIsNone(_clean_and_classify_ioc("CVE-INVALID")[0])
        self.assertIsNone(_clean_and_classify_ioc("not_an_email@")[0])
        self.assertIsNone(_clean_and_classify_ioc("random_word")[0])
        self.assertIsNone(_clean_and_classify_ioc("")[0])

    async def test_02_dynamic_extraction_and_deduplication(self):
        """Verify indicators are dynamically extracted from message text and deduplicated."""
        mock_client = {"client_name": "Test SOC"}

        store.messages["msg_1"] = {
            "id": "msg_1",
            "channel_title": "Darknet Leaks",
            "date": "2026-10-17T10:00:00Z",
            "text": "New exploit CVE-2024-38077 targeting 185.220.101.5. Visit http://darkmarket777.onion for details. Donate bc1qar0srrr7xfkvy5l643lydnw9re59gtzzwf5mdq",
            "threat_level": "HIGH"
        }
        store.messages["msg_2"] = {
            "id": "msg_2",
            "channel_title": "Threat Feed Alpha",
            "date": "2026-10-17T11:00:00Z",
            "text": "Alert on CVE-2024-38077 and IP 185.220.101.5. Contact actor@protonmail.com",
            "threat_level": "HIGH"
        }

        res = await get_iocs_feed(ioc_type="all", limit=50, client=mock_client)

        self.assertEqual(res["status"], "success")
        self.assertEqual(res["client"], "Test SOC")
        iocs = res["iocs"]

        # Deduplication check: duplicate CVE and IP must only appear once
        cves = [i for i in iocs if i["type"] == "cve"]
        self.assertEqual(len(cves), 1)
        self.assertEqual(cves[0]["value"], "CVE-2024-38077")
        self.assertIn(cves[0]["source_message_id"], ["msg_1", "msg_2"])

        ips = [i for i in iocs if i["type"] == "ip"]
        self.assertEqual(len(ips), 1)
        self.assertEqual(ips[0]["value"], "185.220.101.5")

        emails = [i for i in iocs if i["type"] == "email"]
        self.assertEqual(len(emails), 1)
        self.assertEqual(emails[0]["value"], "actor@protonmail.com")

        wallets = [i for i in iocs if i["type"] == "wallet"]
        self.assertEqual(len(wallets), 1)
        self.assertEqual(wallets[0]["value"], "bc1qar0srrr7xfkvy5l643lydnw9re59gtzzwf5mdq")

    async def test_03_ioc_type_filtering(self):
        """Verify filtering by specific ioc_type (cve, ip, domain, email, wallet, hash)."""
        mock_client = {"client_name": "Test SOC"}

        store.messages["msg_test"] = {
            "id": "msg_test",
            "channel_title": "Exploit Group",
            "date": "2026-10-17T12:00:00Z",
            "text": "CVE-2024-1111 found on 192.168.1.50 and host exploit-drop.xyz with wallet 0x71C7656EC7ab88b098defB751B7401B5f6d8976F",
            "threat_level": "MEDIUM"
        }

        # Filter for CVE only
        res_cve = await get_iocs_feed(ioc_type="cve", limit=50, client=mock_client)
        self.assertTrue(all(i["type"] == "cve" for i in res_cve["iocs"]))
        self.assertTrue(any(i["value"] == "CVE-2024-1111" for i in res_cve["iocs"]))

        # Filter for IP only
        res_ip = await get_iocs_feed(ioc_type="ip", limit=50, client=mock_client)
        self.assertTrue(all(i["type"] == "ip" for i in res_ip["iocs"]))
        self.assertTrue(any(i["value"] == "192.168.1.50" for i in res_ip["iocs"]))

        # Filter for Wallet only
        res_wallet = await get_iocs_feed(ioc_type="wallet", limit=50, client=mock_client)
        self.assertTrue(all(i["type"] == "wallet" for i in res_wallet["iocs"]))
        self.assertTrue(any(i["value"] == "0x71C7656EC7ab88b098defB751B7401B5f6d8976F" for i in res_wallet["iocs"]))

    async def test_04_threat_level_filtering_and_empty_results(self):
        """Verify threat level filtering and empty results when criteria don't match."""
        mock_client = {"client_name": "Test SOC"}

        store.messages["msg_low"] = {
            "id": "msg_low",
            "channel_title": "General Chat",
            "date": "2026-10-17T13:00:00Z",
            "text": "Discussing vulnerability CVE-2024-9999",
            "threat_level": "LOW"
        }

        # Query with matching threat level
        res_match = await get_iocs_feed(ioc_type="cve", threat_level="LOW", limit=10, client=mock_client)
        self.assertEqual(res_match["count"], 1)
        self.assertEqual(res_match["iocs"][0]["value"], "CVE-2024-9999")

        # Query with non-matching threat level -> empty results
        res_empty = await get_iocs_feed(ioc_type="cve", threat_level="CRITICAL", limit=10, client=mock_client)
        self.assertEqual(res_empty["count"], 0)
        self.assertEqual(res_empty["iocs"], [])

        # Query for non-existent ioc type -> empty results
        res_no_hash = await get_iocs_feed(ioc_type="hash", limit=10, client=mock_client)
        self.assertEqual(res_no_hash["count"], 0)
        self.assertEqual(res_no_hash["iocs"], [])

    async def test_05_limit_parameter_and_no_data_leak(self):
        """Verify limit parameter is strictly enforced and sensitive fields are not exposed."""
        mock_client = {"client_name": "Test SOC"}

        for idx in range(10):
            store.messages[f"msg_{idx}"] = {
                "id": f"msg_{idx}",
                "channel_title": "Bulk Feed",
                "date": "2026-10-17T14:00:00Z",
                "text": f"Found CVE-2024-{1000 + idx} with secret_pass: password123",
                "threat_level": "HIGH"
            }

        res = await get_iocs_feed(ioc_type="cve", limit=3, client=mock_client)
        self.assertEqual(res["count"], 3)
        self.assertEqual(len(res["iocs"]), 3)

        # Verify sensitive text or credentials are not exposed
        for item in res["iocs"]:
            self.assertNotIn("text", item)
            self.assertNotIn("secret_pass", str(item))
            self.assertIn("type", item)
            self.assertIn("value", item)
            self.assertIn("threat_level", item)
            self.assertIn("source_channel", item)
            self.assertIn("first_seen", item)
            self.assertIn("source_message_id", item)


if __name__ == "__main__":
    unittest.main()
