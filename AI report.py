import json, statistics
from urllib.parse import urlparse

RESULT_FILE = "results.json"
REPORT_HTML = "Report+AI.html"

with open(RESULT_FILE, "r", encoding="utf-8") as f:
    results = json.load(f)

times = [r["load_time"] for r in results]
avg = round(statistics.mean(times), 2) if times else 0
fast = min(results, key=lambda x: x["load_time"]) if results else None
slow = max(results, key=lambda x: x["load_time"]) if results else None
fail = len([r for r in results if any("HTTP status" in i for i in r["issues"])])

sev_count = {"High": 0, "Medium": 0, "Low": 0}

# Page load time categories
good = sum(1 for r in results if 1 <= r["load_time"] <= 3)
average = sum(1 for r in results if 4 <= r["load_time"] <= 8)
poor = sum(1 for r in results if r["load_time"] >= 9)

# Shortened labels (only endpoint)
labels = []
for r in results:
    path = urlparse(r["url"]).path
    labels.append(path if path else r["url"])

cards = ""
for idx, r in enumerate(results):
    sev = "Low"
    if any("HTTP status" in i or "Console" in i or "Visit failed" in i for i in r["issues"]):
        sev = "High"
    elif any("Slow load" in i or "Redirected" in i for i in r["issues"]):
        sev = "Medium"
    sev_count[sev] += 1

    tips = []
    for i in r["issues"]:
        if "Console" in i: tips.append("Fix JavaScript errors.")
        elif "Missing H1" in i: tips.append("Add an H1 heading.")
        elif "Redirected" in i: tips.append("Reduce redirects.")
        elif "Slow load" in i: tips.append("Optimize assets for faster load.")
        elif "HTTP status" in i: tips.append("Check server response.")
        elif "Visit failed" in i: tips.append("Verify page availability.")
    suggestion = "; ".join(tips) if tips else "No issues"

    logs_html = "".join([f"<div class='log-{l['level'].lower()}'>{l['level']} - {l['message']}</div>" for l in r["js_logs"]])
    issues_display = "OK" if not r["issues"] else "Issues: " + ", ".join(r["issues"])

    cards += f"""
    <div class="card {sev}" id="card-{idx}" data-severity="{sev}" data-errorcount="{len(r['issues'])}" data-status="{issues_display}">
        <h3>{r['url']}</h3>
        <p class="status" id="status-{idx}">{issues_display}</p>
        <p><b>Load Time:</b> {r['load_time']:.2f}s | <span class="badge {sev}" id="badge-{idx}">{sev}</span></p>
        <p><b>Visited At:</b> {r['visited_time']}</p>
        <p><b>Suggestions:</b> {suggestion}</p>
        <img src="{r['screenshot']}" class="screenshot" onclick="window.open(this.src)">
        <button class="collapsible">View JS Logs</button>
        <div class="content">{logs_html or '<em>No logs</em>'}</div>
        <button class="ignore-btn" onclick="toggleIgnore({idx})">Ignore Errors</button>
    </div>
    """

html = f"""
<html>
<head>
    <title>Automation Report</title>
    <style>
        body {{ background:#1e1e1e; color:#ddd; font-family:Arial; margin:0; padding:0; }}
        h1,h2,h3 {{ color:#00aaff; }}
        .summary {{ padding:20px; display:flex; justify-content:space-between; align-items:center; flex-wrap:wrap; gap:20px; }}
        .summary-left {{ flex:1; }}
        .search-container {{ display:flex; gap:10px; align-items:center; }}
        .search-container input {{ padding:8px 12px; border:1px solid #00aaff; border-radius:4px; background:#2b2b2b; color:#ddd; font-size:14px; }}
        .search-container button {{ padding:8px 16px; background:#00aaff; color:#000; border:none; border-radius:4px; cursor:pointer; font-weight:bold; }}
        .search-container button:hover {{ background:#00ddff; }}
        .load-btn {{ padding:8px 16px; background:#28a745; color:#fff; border:none; border-radius:4px; cursor:pointer; font-weight:bold; display:flex; align-items:center; gap:8px; }}
        .load-btn:hover {{ background:#32c854; }}
        /* ChatGPT logo styling */
        .chatgpt-logo img {{ width:50px; height:50px; cursor:pointer; }}
        .load-icon {{ font-size:16px; }}
        .cards {{ display:grid; grid-template-columns:repeat(auto-fit, minmax(280px, 1fr)); gap:20px; padding:20px; }}
        .card {{ background:#2b2b2b; border-radius:10px; padding:15px; box-shadow:0 0 10px rgba(0,0,0,0.6); transition:transform .2s; word-wrap:break-word; overflow-wrap:break-word; overflow:visible; position:relative; }}
        .card-id {{ position:absolute; top:10px; left:10px; background:#00aaff; color:#fff; padding:4px 8px; border-radius:4px; font-weight:bold; font-size:12px; z-index:10; }}
        .card:hover {{ transform:scale(1.03); }}
        .card h3 {{ font-size:1rem; color:#00aaff; margin-bottom:10px; word-break:break-all; overflow-wrap:break-word; white-space:normal; line-height:1.4; }}
        .screenshot {{ width:100%; border-radius:8px; margin:10px 0; cursor:pointer; }}
        .badge.High {{ background:#dc3545; padding:2px 6px; border-radius:4px; }}
        .badge.Medium {{ background:#ffc107; padding:2px 6px; border-radius:4px; color:#000; }}
        .badge.Low {{ background:#28a745; padding:2px 6px; border-radius:4px; }}
        .collapsible {{ background:#444; color:#fff; padding:5px; border:none; border-radius:4px; cursor:pointer; }}
        .content {{ display:block; background:#1a1a1a; padding:10px; margin-top:10px; border-radius:4px; border:1px solid #444; z-index:1000; position:relative; }}
        .content.hidden {{ display:none; }}
        .content div {{ margin:5px 0; word-wrap:break-word; overflow-wrap:break-word; white-space:pre-wrap; line-height:1.5; }}
        .ignore-btn {{ background:#007bff; color:#fff; padding:5px; border:none; margin-top:10px; border-radius:4px; cursor:pointer; }}
        .log-info {{ color:cyan; }} .log-warning {{ color:orange; }} .log-severe {{ color:#ff4444; font-weight:bold; }}
        /* Floating AI/Copy Button */
        .ai-copy-btn {{ position:absolute; top:-2px; right:2px; background:transparent; border:none; border-radius:4px; width:38px; height:38px; cursor:pointer; padding:2px; display:flex; align-items:center; justify-content:center; z-index:20; transition:all 0.3s ease; }}
        .ai-copy-btn img {{ width:34px; height:34px; object-fit:contain; }}
        .ai-copy-btn:hover {{ transform:scale(1.15); }}
        .ai-copy-btn:active {{ transform:scale(0.95); }}
    </style>
</head>
<body>
    <div class="summary">
        <div class="summary-left">
            <h1>Automation Report</h1>
            <p id="universityName"><b>University Name:</b> <span id="uniNameValue">{results[0]['url'].split('.')[1] if results else 'Unknown'}</span></p>
            <p id="pageSummary"><b>Total Pages:</b> {len(results)} | <b>Failed:</b> {fail}</p>
            <p><b>Average Load:</b> {avg}s</p>
            <p><b>Fastest:</b> {fast['url'] if fast else '-'} ({fast['load_time'] if fast else '-'})</p>
            <p><b>Slowest:</b> {slow['url'] if slow else '-'} ({slow['load_time'] if slow else '-'})</p>
            <p><b>Page Load Categories:</b> 
                <span style="color:green">Good - {good}</span> | 
                <span style="color:yellow">Average - {average}</span> | 
                <span style="color:red">Poor - {poor}</span>
            </p>
        </div>
        <!-- optionally place an icon next to the search box -->
        <div class="chatgpt-logo">
            <img src="chatgpt.png" alt="ChatGPT" title="Open ChatGPT" onclick="window.open('https://chat.openai.com','_blank')">
        </div>
        <div class="search-container">
            <input type="text" id="searchInput" placeholder="Search URL...">
            <button onclick="searchCards()">Search</button>
            <button class="load-btn" onclick="loadAllRecords()"><span class="load-icon">⟳</span> REPORT LOAD</button>
        </div>
    </div>
    <div class="cards">{cards}</div>
    <script>
        let ignored = Array(226).fill(false);

        // Add ID numbers to each card
        function addCardIds() {{
            const cards = document.querySelectorAll('.card');
            cards.forEach((card, index) => {{
                if (!card.querySelector('.card-id')) {{
                    const idNumber = String(index + 1).padStart(2, '0');
                    const idBadge = document.createElement('div');
                    idBadge.className = 'card-id';
                    idBadge.textContent = `ID-${{idNumber}}`;
                    card.insertBefore(idBadge, card.firstChild);
                }}
            }});
        }}

        // Extract university name from URL
        function extractUniversityName() {{
            const firstCard = document.querySelector('.card h3');
            if (firstCard) {{
                const url = firstCard.textContent;
                const match = url.match(/https?:\/\/[a-z.]+\.([a-z]+\.edu\.in)/);
                if (match) {{
                    const domain = match[1];
                    const universityName = domain.split('.')[0];
                    document.getElementById('uniNameValue').textContent = universityName;
                }}
            }}
        }}

        // Call on page load
        window.addEventListener('load', function() {{
            addCardIds();
            extractUniversityName();
        }});
        addCardIds();
        extractUniversityName();

        document.querySelectorAll('.collapsible').forEach(b => b.onclick = function() {{
            this.classList.toggle('active');
            var c = this.nextElementSibling;
            c.classList.toggle('hidden');
            this.textContent = c.classList.contains('hidden') ? 'View JS Logs' : 'Hide JS Logs';
        }});

        function searchCards() {{
            const searchTerm = document.getElementById('searchInput').value.toLowerCase().trim();
            const cards = document.querySelectorAll('.card');
            let visibleCount = 0;

            cards.forEach(card => {{
                const urlText = card.querySelector('h3').textContent.toLowerCase();
                const idBadge = card.querySelector('.card-id');
                const cardId = idBadge ? idBadge.textContent.toLowerCase() : '';
                
                let isMatch = false;
                
                if (searchTerm === '') {{
                    // Don't show any records if search is empty
                    isMatch = false;
                }} else {{
                    // Search by URL
                    if (urlText.includes(searchTerm)) {{
                        isMatch = true;
                    }}
                    
                    // Search by ID - handle different formats
                    if (cardId) {{
                        // Extract just the number from cardId (e.g., "id-01" -> "01")
                        const idNumber = cardId.replace(/[^\d]/g, '');
                        const searchTermClean = searchTerm.replace(/[^\d]/g, '');
                        
                        // Match if search term is in cardId or just the number
                        if (cardId.includes(searchTerm) || idNumber === searchTermClean) {{
                            isMatch = true;
                        }}
                    }}
                }}
                
                card.style.display = isMatch ? '' : 'none';
                if (isMatch) visibleCount++;
            }});

            if (searchTerm !== '') {{
                alert(`Found ${{visibleCount}} matching record(s)`);
            }}
        }}

        function loadAllRecords() {{
            const cards = document.querySelectorAll('.card');
            cards.forEach(card => {{
                card.style.display = '';
        }});
            document.getElementById('searchInput').value = '';
        }}

        document.getElementById('searchInput').addEventListener('keypress', function(e) {{
            if (e.key === 'Enter') {{
                searchCards();
            }}
        }});

        /* Copy card content and open ChatGPT */
        function copyAndOpenChatGPT(cardElement) {{
            const cardText = cardElement.innerText;
            const cardURL = cardElement.querySelector('h3')?.innerText || 'Unknown URL';
            const prompt = `Please analyze this automation test report card:\n\n${{cardText}}\n\nProvide insights on the issues, suggest fixes, and recommend improvements.`;
            const encodedPrompt = encodeURIComponent(prompt);
            const chatgptURL = `https://chat.openai.com/?q=${{encodedPrompt}}`;
            window.open(chatgptURL, '_blank');
        }}

        /* Add AI copy button to all cards after page loads */
        window.addEventListener('load', function() {{
            const cards = document.querySelectorAll('.card');
            cards.forEach(card => {{
                if (!card.querySelector('.ai-copy-btn')) {{
                    const btn = document.createElement('button');
                    btn.className = 'ai-copy-btn';
                    btn.title = 'Copy to ChatGPT';
                    btn.innerHTML = '<img src="ai-copy-btn.png" alt="Copy">';
                    btn.onclick = function(e) {{
                        e.stopPropagation();
                        copyAndOpenChatGPT(card);
                    }};
                    card.appendChild(btn);   
                }}
            }});
        }});
    </script>
</body>
</html>
"""

with open(REPORT_HTML, "w", encoding="utf-8") as f:
    f.write(html)
print(f"📄 Final report generated: {REPORT_HTML}")