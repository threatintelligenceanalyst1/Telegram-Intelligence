import re
from typing import List, Dict, Any, Optional, Tuple

SECTORS_LIST: List[str] = [
    "All Sectors",
    "Banking & Financial Services",
    "FinTech & Payments",
    "Cybersecurity",
    "Technology & Software",
    "Healthcare",
    "E-commerce",
    "Telecommunications",
    "Government",
    "Education",
    "Aviation",
    "Automotive",
    "Energy",
    "Defense",
    "Retail",
    "Logistics",
    "Other / General"
]

SECTOR_TAXONOMY: Dict[str, Dict[str, Any]] = {
    "Banking & Financial Services": {
        "icon": "Building2",
        "keywords": [
            "bank", "banking", "account", "credit card", "debit card", "atm", "branch",
            "ifsc", "swift", "wire transfer", "deposit", "fixed deposit", "loan", "mortgage",
            "overdraft", "cheque", "netbanking", "savings account", "current account",
            "transaction", "statement", "kyc", "cibil", "rbi", "federal reserve",
            "vault", "bank logs", "bank drop", "carding", "pin", "cvv", "cvv2",
            "hdfc", "sbi", "icici", "axis bank", "pnb", "kotak", "canara bank", "bank of baroda",
            "chase", "wells fargo", "citibank", "hsbc", "barclays", "bank of america",
            "capital one", "standard chartered", "deutsche bank", "santander"
        ],
        "disqualifiers": [
            r"\bblood[\s\-]*bank\b",
            r"\bfood[\s\-]*bank\b",
            r"\briver[\s\-]*bank\b",
            r"\briverbank\b",
            r"\bpower[\s\-]*bank\b",
            r"\bseed[\s\-]*bank\b",
            r"\bsperm[\s\-]*bank\b",
            r"\bmemory[\s\-]*bank\b",
            r"\beye[\s\-]*bank\b",
            r"\borgan[\s\-]*bank\b",
            r"\bsand[\s\-]*bank\b",
            r"\bcloud[\s\-]*bank\b",
            r"\bbank\s+of\s+the\s+river\b",
            r"\bleft\s+bank\b",
            r"\bright\s+bank\b"
        ],
        "essential_financial_markers": [
            "account", "credit", "debit", "card", "loan", "deposit", "branch", "ifsc", "atm",
            "balance", "transaction", "statement", "kyc", "swift", "wire", "vault", "cheque",
            "netbanking", "banking", "hdfc", "sbi", "icici", "axis", "pnb", "kotak", "chase",
            "wells fargo", "citi", "credentials", "login", "pin", "cvv", "money", "funds"
        ]
    },
    "FinTech & Payments": {
        "icon": "CreditCard",
        "keywords": [
            "payment", "gateway", "upi", "paytm", "phonepe", "gpay", "google pay", "razorpay",
            "stripe", "paypal", "crypto", "cryptocurrency", "bitcoin", "btc", "ethereum", "eth",
            "usdt", "tether", "binance", "coinbase", "wallet", "seed phrase", "private key",
            "escrow", "pos", "qr code", "fintech", "remittance", "p2p payment", "merchant"
        ],
        "disqualifiers": [
            r"\bpayment\s+due\s+to\s+illness\b"
        ]
    },
    "Cybersecurity": {
        "icon": "ShieldAlert",
        "keywords": [
            "cve", "vulnerability", "exploit", "zero-day", "0day", "malware", "ransomware",
            "trojan", "backdoor", "rat", "stealer", "redline", "infostealer", "botnet", "ddos",
            "payload", "shellcode", "reverse shell", "webshell", "rootkit", "sql injection",
            "xss", "rce", "phishing", "credential stuffing", "database dump", "leak", "combolist",
            "hashcat", "mimikatz", "metasploit", "threat actor", "ioc", "darknet", "breach"
        ],
        "disqualifiers": [
            r"\bsea[\s\-]*shell\b",
            r"\btortoise[\s\-]*shell\b",
            r"\begg[\s\-]*shell\b"
        ]
    },
    "Technology & Software": {
        "icon": "Cpu",
        "keywords": [
            "software", "code", "github", "gitlab", "source code", "api", "api key", "server",
            "linux", "windows", "database", "mongodb", "mysql", "postgresql", "python", "javascript",
            "docker", "kubernetes", "cloud", "aws", "azure", "gcp", "ssh", "rdp", "vps", "vpn",
            "backend", "frontend", "devops", "git", "token", "access token", "sdk"
        ],
        "disqualifiers": [
            r"\bapple\s+pie\b",
            r"\bapple\s+juice\b",
            r"\bapple\s+tree\b"
        ]
    },
    "Healthcare": {
        "icon": "HeartPulse",
        "keywords": [
            "hospital", "patient", "medical", "doctor", "health", "clinical", "pharma",
            "pharmaceutical", "drug", "prescription", "blood bank", "donor", "vaccine",
            "ehr", "emr", "diagnosis", "surgery", "treatment", "pathology", "laboratory"
        ],
        "disqualifiers": []
    },
    "E-commerce": {
        "icon": "ShoppingCart",
        "keywords": [
            "shop", "store", "order", "cart", "checkout", "amazon", "flipkart", "ebay",
            "shopify", "woocommerce", "customer data", "shipping", "tracking", "refund",
            "invoice", "discount", "coupon", "voucher", "buyer", "seller", "marketplace"
        ],
        "disqualifiers": []
    },
    "Telecommunications": {
        "icon": "Radio",
        "keywords": [
            "telecom", "sim", "sim swap", "esim", "sms", "call", "carrier", "airtel", "jio",
            "vodafone", "vi", "bsnl", "verizon", "at&t", "t-mobile", "imsi", "imei", "cell tower",
            "voip", "otp bypass", "call forwarding", "broadband", "isp", "fiber"
        ],
        "disqualifiers": []
    },
    "Government": {
        "icon": "Landmark",
        "keywords": [
            "government", "gov", "ministry", "department", "national", "federal", "passport",
            "aadhaar", "pan card", "voter id", "driving license", "tax", "irs", "income tax",
            "police", "court", "judiciary", "public sector", "official portal", "nic", "citizen"
        ],
        "disqualifiers": []
    },
    "Education": {
        "icon": "GraduationCap",
        "keywords": [
            "school", "college", "university", "student", "exam", "examination", "question paper",
            "answer key", "marksheet", "degree", "diploma", "syllabus", "admission", "campus",
            "faculty", "professor", "academic", "institution", "education board", "cbse", "sppu"
        ],
        "disqualifiers": []
    },
    "Aviation": {
        "icon": "Plane",
        "keywords": [
            "airline", "airport", "flight", "pilot", "aircraft", "boeing", "airbus",
            "boarding pass", "radar", "atc", "air traffic", "icao", "iata", "cockpit", "aviation"
        ],
        "disqualifiers": []
    },
    "Automotive": {
        "icon": "Car",
        "keywords": [
            "car", "vehicle", "automobile", "auto", "motor", "vin", "telematics", "ecu",
            "can bus", "ev", "electric vehicle", "tesla", "fleet", "dealer", "dealership"
        ],
        "disqualifiers": []
    },
    "Energy": {
        "icon": "Zap",
        "keywords": [
            "oil", "gas", "petroleum", "power grid", "electricity", "nuclear", "solar",
            "wind power", "pipeline", "refinery", "scada", "ics", "substation", "generator"
        ],
        "disqualifiers": []
    },
    "Defense": {
        "icon": "Shield",
        "keywords": [
            "military", "army", "navy", "air force", "defense", "defence", "weapon",
            "missile", "radar", "classified", "intelligence agency", "espionage", "pentagon", "mod"
        ],
        "disqualifiers": []
    },
    "Retail": {
        "icon": "Store",
        "keywords": [
            "retail", "supermarket", "grocery", "pos system", "cash register", "inventory",
            "merchandise", "outlet", "chain store", "warehouse club", "stock"
        ],
        "disqualifiers": []
    },
    "Logistics": {
        "icon": "Truck",
        "keywords": [
            "logistics", "cargo", "freight", "shipping line", "courier", "container",
            "supply chain", "customs", "delivery", "fedex", "dhl", "ups", "tracking number"
        ],
        "disqualifiers": []
    },
    "Other / General": {
        "icon": "Folder",
        "keywords": [],
        "disqualifiers": []
    }
}


class ContextSearchEngine:
    """
    Context-Aware Cyber Threat Intelligence Search & Confidence Scoring Engine.
    Evaluates semantic sector relevance, identifies false positives (e.g. 'blood bank' vs financial banks),
    and assigns calibrated confidence scores to search results.
    """

    @classmethod
    def get_supported_sectors(cls) -> List[str]:
        return SECTORS_LIST

    @classmethod
    def evaluate_message(
        cls,
        message: Dict[str, Any],
        query: str,
        sector_filter: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Calculates confidence score, detects primary sector, extracts context keywords,
        and flags disqualifications.
        """
        text = str(message.get("text") or "")
        sender = str(message.get("sender") or "")
        channel_name = str(message.get("channel_username") or "")
        combined_text = f"{text} {sender} {channel_name}".lower()

        q_clean = query.strip().lower()
        if not q_clean:
            return {
                "confidence_score": 0,
                "confidence_level": "LOW",
                "detected_sector": "Other / General",
                "matched_context_keywords": [],
                "is_contextual_match": False,
                "is_disqualified": False,
                "relevance_reason": "No query provided"
            }

        target_sector = sector_filter if sector_filter and sector_filter != "All Sectors" else None

        # 1. Base Query Match Score (0 - 35)
        base_score = 0
        q_exact_pattern = re.compile(rf"\b{re.escape(q_clean)}\b", re.IGNORECASE)
        if q_exact_pattern.search(text):
            base_score += 30
        elif q_clean in text.lower():
            base_score += 20
        elif q_clean in sender.lower() or q_clean in channel_name.lower():
            base_score += 15

        # 2. Sector Keyword Density & Entity Detection
        sector_scores: Dict[str, int] = {}
        sector_matched_words: Dict[str, List[str]] = {}

        for sec_name, sec_data in SECTOR_TAXONOMY.items():
            if sec_name == "Other / General":
                continue
            matched = []
            score = 0
            for kw in sec_data["keywords"]:
                # Don't duplicate score if keyword is literally the search query itself
                if kw == q_clean:
                    continue
                kw_pat = re.compile(rf"\b{re.escape(kw)}\b", re.IGNORECASE)
                if kw_pat.search(combined_text):
                    matched.append(kw)
                    score += 8

            sector_scores[sec_name] = score
            sector_matched_words[sec_name] = matched

        # Determine best detected sector
        detected_sector = "Other / General"
        max_sec_score = 0
        for s_name, s_score in sector_scores.items():
            if s_score > max_sec_score:
                max_sec_score = s_score
                detected_sector = s_name

        # If user selected a specific sector, prioritize analyzing against it
        active_sector = target_sector if target_sector else detected_sector
        active_sec_data = SECTOR_TAXONOMY.get(active_sector, {})
        matched_kw = sector_matched_words.get(active_sector, [])

        # 3. Disqualifier / False-Positive Penalty Detection
        is_disqualified = False
        disqualifier_penalty = 0
        matched_disqualifier = None

        if active_sec_data.get("disqualifiers"):
            for disq_regex in active_sec_data["disqualifiers"]:
                if re.search(disq_regex, combined_text, re.IGNORECASE):
                    matched_disqualifier = disq_regex
                    # Check if there are strong positive financial markers to override or if it's purely non-banking
                    essential_markers = active_sec_data.get("essential_financial_markers", [])
                    has_strong_override = any(
                        re.search(rf"\b{re.escape(marker)}\b", combined_text, re.IGNORECASE)
                        for marker in essential_markers
                        if marker != q_clean
                    )
                    if not has_strong_override:
                        # Complete false positive (e.g. purely "blood bank" or "river bank")
                        is_disqualified = True
                        disqualifier_penalty = 80
                    else:
                        # Ambiguous / partial penalty
                        disqualifier_penalty = 40
                    break

        # 4. Context Boost Calculation
        context_boost = 0
        if target_sector:
            # User specifically asked for this sector!
            kw_count = len(matched_kw)
            if kw_count >= 3:
                context_boost = 45
            elif kw_count == 2:
                context_boost = 35
            elif kw_count == 1:
                context_boost = 25
            else:
                # Query matches alone with no sector context
                context_boost = 5
        else:
            # All Sectors mode: boost based on any natural detected sector context
            if len(matched_kw) >= 2:
                context_boost = 25
            elif len(matched_kw) == 1:
                context_boost = 15

        # 5. Cyber Threat Intelligence Indicator Boost (0 - 20)
        threat_boost = 0
        threat_level = message.get("threat_level", "LOW")
        if threat_level in ["CRITICAL", "HIGH"]:
            threat_boost += 10
        elif threat_level == "MEDIUM":
            threat_boost += 5

        # Check for credential / CVE / Onion / IOC mentions
        if re.search(r"\b(cve-\d{4}-\d+|leak|dump|password|credentials?|breach|combo|\.onion)\b", combined_text, re.IGNORECASE):
            threat_boost += 10

        # 6. Aggregate Raw Score & Normalization
        raw_score = base_score + context_boost + threat_boost - disqualifier_penalty

        # If disqualified, force to very low or zero
        if is_disqualified:
            final_score = max(0, min(20, raw_score))
        else:
            final_score = max(10, min(100, raw_score))

        # Confidence Level Tier
        if final_score >= 75:
            confidence_level = "HIGH"
        elif final_score >= 45:
            confidence_level = "MEDIUM"
        else:
            confidence_level = "LOW"

        # Contextual match flag
        is_contextual = final_score >= 45 and not is_disqualified

        # Explainable Reason
        if is_disqualified:
            reason = f"Filtered out: Matched false-positive expression ({matched_disqualifier}) with no {active_sector} context."
        elif len(matched_kw) > 0:
            top_kws = ", ".join(matched_kw[:4])
            reason = f"Context verified in {active_sector}: matched domain keywords ({top_kws})."
        else:
            reason = "Keyword match with baseline contextual confidence."

        return {
            "confidence_score": int(final_score),
            "confidence_level": confidence_level,
            "detected_sector": active_sector if len(matched_kw) > 0 else detected_sector,
            "matched_context_keywords": matched_kw[:6],
            "is_contextual_match": is_contextual,
            "is_disqualified": is_disqualified,
            "relevance_reason": reason
        }

    @classmethod
    def score_and_filter_results(
        cls,
        results: List[Dict[str, Any]],
        query: str,
        sector_filter: Optional[str] = None,
        min_confidence: Optional[int] = None
    ) -> Tuple[List[Dict[str, Any]], Dict[str, int]]:
        """
        Enriches candidate messages with context intelligence, filters out false positives,
        ranks by confidence score, and returns sector distribution metrics.
        """
        target_sector = sector_filter if sector_filter and sector_filter != "All Sectors" else None
        effective_min_confidence = min_confidence if min_confidence is not None else (40 if target_sector else 0)

        enriched_results = []
        sector_stats: Dict[str, int] = {}

        for msg in results:
            eval_data = cls.evaluate_message(msg, query, target_sector)

            # If a specific sector is selected and message is disqualified (e.g. 'blood bank' in Banking), DROP IT
            if target_sector and eval_data["is_disqualified"]:
                continue

            # Check confidence threshold
            if eval_data["confidence_score"] < effective_min_confidence:
                continue

            # Merge evaluation fields into message result
            enriched_msg = dict(msg)
            enriched_msg["confidence_score"] = eval_data["confidence_score"]
            enriched_msg["confidence_level"] = eval_data["confidence_level"]
            enriched_msg["detected_sector"] = eval_data["detected_sector"]
            enriched_msg["matched_context_keywords"] = eval_data["matched_context_keywords"]
            enriched_msg["is_contextual_match"] = eval_data["is_contextual_match"]
            enriched_msg["relevance_reason"] = eval_data["relevance_reason"]

            enriched_results.append(enriched_msg)

            # Aggregate sector metrics
            det_sec = eval_data["detected_sector"]
            sector_stats[det_sec] = sector_stats.get(det_sec, 0) + 1

        # Sort by confidence score descending, then date descending
        enriched_results.sort(
            key=lambda x: (x.get("confidence_score", 0), str(x.get("date", ""))),
            reverse=True
        )

        return enriched_results, sector_stats
