import os
import tempfile
import unittest
from app import create_app

class ApiComprehensiveTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
        self.tmp.close()
        os.environ["ENABLE_SCHEDULER"] = "0"
        self.app = create_app()
        self.app.config.update(TESTING=True, DATABASE_PATH=self.tmp.name, ENABLE_SCHEDULER=False)
        from database import init_db
        init_db(self.tmp.name)
        self.client = self.app.test_client()

    def tearDown(self):
        try:
            os.unlink(self.tmp.name)
        except Exception:
            pass

    def test_health_and_index(self):
        with self.app.test_client() as client:
            res = client.get("/health")
            self.assertEqual(res.status_code, 200)
            self.assertTrue(res.get_json()["ok"])

            index_res = client.get("/")
            self.assertEqual(index_res.status_code, 200)
            self.assertIn("Subscription Killer API", index_res.get_json()["name"])

    def test_req1_transaction_id_no_bank_details(self):
        """Req 1: Works strictly from Transaction ID; no bank details needed"""
        with self.app.test_client() as client:
            res = client.post("/api/subscriptions", json={
                "user_id": 1,
                "transaction_ref": "TXN-TEST-9988",
                "merchant": "Figma Pro",
                "amount": 1200,
                "renewal_date": "2026-12-01",
                "cancellation_deadline": "2026-11-29"
            })
            self.assertEqual(res.status_code, 201)
            sub = res.get_json()["subscription"]
            self.assertEqual(sub["transaction_ref"], "TXN-TEST-9988")
            self.assertEqual(sub["merchant"], "Figma Pro")

            # Look up subscription directly by transaction_id
            by_txn = client.get("/api/subscriptions/by-transaction/TXN-TEST-9988")
            self.assertEqual(by_txn.status_code, 200)
            self.assertEqual(by_txn.get_json()["subscription"]["merchant"], "Figma Pro")

    def test_req2_direct_cancellation(self):
        """Req 2: Direct cancellation immediately terminates subscription and confirms"""
        with self.app.test_client() as client:
            # Create sub
            sub_res = client.post("/api/subscriptions", json={
                "user_id": 1,
                "transaction_ref": "TXN-CANCEL-001",
                "merchant": "Gym Plan",
                "amount": 2500,
                "renewal_date": "2026-11-15"
            })
            sub_id = sub_res.get_json()["subscription"]["subscription_id"]

            # Direct cancel
            cancel_res = client.post(f"/api/subscriptions/{sub_id}/cancel")
            self.assertEqual(cancel_res.status_code, 200)
            data = cancel_res.get_json()
            self.assertTrue(data["success"])
            self.assertEqual(data["subscription_status"], "cancelled")
            self.assertIn("KILL-", data["confirmation_code"])
            self.assertGreater(data["points_awarded"], 0)

            # Direct cancel by transaction id
            sub_res2 = client.post("/api/subscriptions", json={
                "user_id": 1,
                "transaction_ref": "TXN-CANCEL-002",
                "merchant": "Box Membership",
                "amount": 800,
                "renewal_date": "2026-11-20"
            })
            cancel_by_txn = client.post("/api/subscriptions/cancel-by-transaction", json={
                "transaction_ref": "TXN-CANCEL-002"
            })
            self.assertEqual(cancel_by_txn.status_code, 200)
            self.assertEqual(cancel_by_txn.get_json()["subscription_status"], "cancelled")

    def test_req3_notifications_as_per_user_inputs(self):
        """Req 3: Custom notifications created and configured as per user inputs"""
        with self.app.test_client() as client:
            # Update user notification preferences
            pref_res = client.put("/api/notification-preferences", json={
                "user_id": 1,
                "reminder_days": [14, 7, 2, 0],
                "audio_alerts": True,
                "in_app_enabled": True
            })
            self.assertEqual(pref_res.status_code, 200)
            self.assertEqual(pref_res.get_json()["reminder_days"], [14, 7, 2, 0])

            # Create custom notification directly from user input
            custom_notif = client.post("/api/notifications", json={
                "user_id": 1,
                "title": "Don't forget to review Netflix",
                "message": "User custom alert: review Netflix usage before weekend",
                "transaction_ref": "TXN-NTFLX-8921"
            })
            self.assertEqual(custom_notif.status_code, 201)
            notifs = client.get("/api/notifications?user_id=1")
            self.assertEqual(notifs.status_code, 200)
            self.assertGreaterEqual(len(notifs.get_json()["notifications"]), 1)

    def test_req4_cancellation_deadlines(self):
        """Req 4: Deadlines for cancellation of subscription calculated and tracked"""
        with self.app.test_client() as client:
            res = client.post("/api/subscriptions", json={
                "user_id": 1,
                "transaction_ref": "TXN-DEADLINE-1",
                "merchant": "Software Cloud",
                "amount": 999,
                "renewal_date": "2026-12-20",
                "cancellation_deadline": "2026-12-18"
            })
            sub_id = res.get_json()["subscription"]["subscription_id"]

            deadline_res = client.get(f"/api/subscriptions/{sub_id}/deadline")
            self.assertEqual(deadline_res.status_code, 200)
            dl = deadline_res.get_json()["deadline"]
            self.assertEqual(dl["cancellation_deadline"], "2026-12-18")
            self.assertIsNotNone(dl["days_remaining"])
            self.assertIn(dl["urgency"], ["UPCOMING", "WARNING", "CRITICAL", "EXPIRED"])

            all_dl = client.get("/api/subscriptions/deadlines?user_id=1")
            self.assertEqual(all_dl.status_code, 200)
            self.assertGreater(len(all_dl.get_json()["deadlines"]), 0)

    def test_req5_credit_scores_allotted_on_cancelling_or_upgrading(self):
        """Req 5: Credit scores allotted when user cancels or upgrades"""
        with self.app.test_client() as client:
            score_initial = client.get("/api/score?user_id=1").get_json()["credit_score"]

            # Sub 1: Cancel
            sub1 = client.post("/api/subscriptions", json={
                "user_id": 1, "transaction_ref": "TXN-SC-1", "merchant": "Unused Service", "amount": 500
            }).get_json()["subscription"]
            cancel_res = client.post(f"/api/subscriptions/{sub1['subscription_id']}/cancel").get_json()
            self.assertEqual(cancel_res["points_awarded"], 50)

            # Sub 2: Upgrade
            sub2 = client.post("/api/subscriptions", json={
                "user_id": 1, "transaction_ref": "TXN-SC-2", "merchant": "Useful Tool", "amount": 300
            }).get_json()["subscription"]
            upgrade_res = client.post(f"/api/subscriptions/{sub2['subscription_id']}/upgrade", json={
                "new_plan": "Enterprise Pro",
                "new_amount": 600
            }).get_json()
            self.assertEqual(upgrade_res["points_awarded"], 30)

            score_final = client.get("/api/score?user_id=1").get_json()
            self.assertGreater(score_final["credit_score"], score_initial)
            self.assertGreaterEqual(score_final["cancellations_count"], 1)
            self.assertGreaterEqual(score_final["upgrades_count"], 1)

            # Score history
            history = client.get("/api/score/history?user_id=1").get_json()
            self.assertGreaterEqual(len(history["entries"]), 2)

    def test_req6_audio_io_7_languages(self):
        """Req 6: Audio I/O for English, Hindi, Marathi, Tamil, Telugu, Bengali, Gujarati"""
        with self.app.test_client() as client:
            lang_res = client.get("/api/voice/languages")
            self.assertEqual(lang_res.status_code, 200)
            codes = [item["code"] for item in lang_res.get_json()["supported_languages"]]
            for target_lang in ["en", "hi", "mr", "ta", "te", "bn", "gu"]:
                self.assertIn(target_lang, codes)

            # Test text-to-speech for all 7 languages
            for lang in ["en", "hi", "mr", "ta", "te", "bn", "gu"]:
                tts_res = client.post("/api/voice/speak", json={
                    "text": "SubKiller testing speech output",
                    "language": lang
                })
                self.assertEqual(tts_res.status_code, 200, f"TTS failed for {lang}")
                data = tts_res.get_json()
                self.assertTrue(len(data["audio_base64"]) > 50)
                self.assertEqual(data["language"], lang)
                self.assertTrue(data["audio_data_url"].startswith("data:audio/"))

            # Test voice assistant chat turn
            chat_res = client.post("/api/voice/assistant-chat", json={
                "query": "What is my credit score?",
                "language": "hi",
                "user_id": 1
            })
            self.assertEqual(chat_res.status_code, 200)
            self.assertTrue(len(chat_res.get_json()["audio_data_url"]) > 50)

    def test_req7_elevenlabs_linguistic_integration(self):
        """Req 7: ElevenLabs linguistic voices catalog, verify-key, and TTS synthesis"""
        with self.app.test_client() as client:
            # 1. Fetch ElevenLabs voices catalog
            voices_res = client.get("/api/voice/elevenlabs/voices")
            self.assertEqual(voices_res.status_code, 200)
            voices_data = voices_res.get_json()
            self.assertIn("voices", voices_data)
            self.assertGreaterEqual(len(voices_data["voices"]), 4)
            # Rachel should be in curated list
            voice_names = [v["name"] for v in voices_data["voices"]]
            self.assertIn("Rachel", voice_names)
            self.assertIn("models", voices_data)

            # 2. Key verification (returns valid or informative error without 500)
            verify_res = client.post("/api/voice/elevenlabs/verify-key", json={"api_key": ""})
            self.assertEqual(verify_res.status_code, 200)
            self.assertFalse(verify_res.get_json()["valid"])

            # 3. Explicit ElevenLabs speak endpoint (with resilient fallback)
            el_speak_res = client.post("/api/voice/elevenlabs/speak", json={
                "text": "Subscription Killer direct cancellation completed.",
                "language": "en",
                "voice_id": "21m00Tcm4TlvDq8ikWAM"
            })
            self.assertEqual(el_speak_res.status_code, 200)
            el_data = el_speak_res.get_json()
            self.assertTrue(len(el_data["audio_base64"]) > 50)
            self.assertTrue(el_data["audio_data_url"].startswith("data:audio/"))

            # 4. Standard speak endpoint with provider=elevenlabs
            prov_speak_res = client.post("/api/voice/speak", json={
                "text": "नमस्ते, आपका सब्सक्रिप्शन रद्द हो गया है।",
                "language": "hi",
                "provider": "elevenlabs"
            })
            self.assertEqual(prov_speak_res.status_code, 200)
            self.assertTrue(len(prov_speak_res.get_json()["audio_base64"]) > 50)

    def test_req8_batch_subscription_sync(self):
        """Req 8: Batch create / sync detected subscriptions by Transaction ID"""
        with self.app.test_client() as client:
            batch_res = client.post("/api/subscriptions/batch", json={
                "user_id": 1,
                "subscriptions": [
                    {
                        "merchant": "Netflix India",
                        "transaction_ref": "TXN-NETFLIX-901",
                        "amount": 649,
                        "plan_name": "Premium",
                        "f": "M"
                    },
                    {
                        "merchant": "Spotify India",
                        "transaction_ref": "TXN-SPOTIFY-902",
                        "amount": 139,
                        "plan_name": "Individual",
                        "f": "M"
                    }
                ]
            })
            self.assertEqual(batch_res.status_code, 200)
            data = batch_res.get_json()
            self.assertEqual(data["count"], 2)
            self.assertEqual(data["subscriptions"][0]["merchant"], "Netflix India")
            self.assertEqual(data["subscriptions"][0]["transaction_ref"], "TXN-NETFLIX-901")

if __name__ == "__main__":
    unittest.main()

