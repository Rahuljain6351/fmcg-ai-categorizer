from fastapi import FastAPI, HTTPException
from fastapi.responses import HTMLResponse
from pydantic import BaseModel
import ollama
import json

app = FastAPI(title="FMCG Inventory Categorizer")

class InventoryItem(BaseModel):
    raw_name: str

@app.get("/")
def serve_ui():
    html_content = """
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>AI Inventory Categorizer</title>
        <script src="https://cdn.tailwindcss.com"></script>
    </head>
    <body class="bg-slate-100 p-6 font-sans text-slate-800 h-screen flex flex-col">
        <div class="max-w-6xl mx-auto w-full space-y-6 flex-grow">
            
            <!-- Header & Analytics -->
            <div class="bg-white p-5 rounded-xl shadow-sm border border-slate-200 flex flex-wrap justify-between items-center gap-4">
                <div>
                    <h1 class="text-2xl font-extrabold flex items-center gap-2"><span class="text-3xl">📦</span> Smart Inventory AI</h1>
                    <p class="text-slate-500 text-sm mt-1">Human-in-the-Loop (HITL) System: AI processes, Humans verify.</p>
                </div>
                
                <!-- Live Stats -->
                <div class="flex gap-4 bg-slate-50 p-2 rounded-lg border border-slate-200">
                    <div class="text-center px-4 border-r border-slate-200">
                        <p class="text-xs font-bold text-slate-400 uppercase">Processed</p>
                        <p id="statTotal" class="text-xl font-black text-blue-600">0</p>
                    </div>
                    <div class="text-center px-4">
                        <p class="text-xs font-bold text-slate-400 uppercase">Needs Review</p>
                        <p id="statReview" class="text-xl font-black text-red-500">0</p>
                    </div>
                </div>

                <div class="flex gap-2">
                    <button onclick="clearAll()" class="bg-red-50 hover:bg-red-100 text-red-600 px-4 py-2 rounded-lg font-bold border border-red-200 transition text-sm">Clear</button>
                    <button onclick="downloadCSV()" class="bg-emerald-600 hover:bg-emerald-700 text-white px-4 py-2 rounded-lg font-bold shadow-md transition flex items-center gap-2 text-sm">⬇️ Export CSV</button>
                </div>
            </div>

            <div class="grid grid-cols-1 lg:grid-cols-4 gap-6 h-[calc(100vh-180px)]">
                <!-- Input Section -->
                <div class="lg:col-span-1 bg-white p-5 rounded-xl shadow-sm border border-slate-200 flex flex-col h-full">
                    <label class="block text-sm font-bold text-slate-700 mb-2">Raw Product Strings</label>
                    <textarea id="rawName" rows="8" placeholder="Paste items here..." 
                           class="w-full flex-grow p-3 border border-slate-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500 mb-3 text-sm font-mono whitespace-pre resize-none"></textarea>
                    
                    <div class="bg-slate-50 p-3 rounded-lg border border-slate-200 mb-4">
                        <label class="block text-xs font-bold text-slate-500 uppercase tracking-wider mb-2">Test Data Generator</label>
                        <div class="flex items-center gap-2">
                            <input type="number" id="testCount" value="6" min="1" max="10" 
                                   class="w-16 p-2 text-sm border border-slate-300 rounded focus:outline-none text-center font-bold">
                            <button onclick="generateRandomItems()" class="w-full text-sm bg-white hover:bg-slate-100 px-3 py-2 rounded border border-slate-300 font-bold text-blue-600 transition shadow-sm">🎲 Load</button>
                        </div>
                    </div>
                    
                    <button onclick="categorize()" id="submitBtn" class="w-full bg-blue-600 text-white font-bold py-3 rounded-lg hover:bg-blue-700 transition shadow-md">
                        Process Batch
                    </button>
                </div>

                <!-- Data Table Section -->
                <div class="lg:col-span-3 bg-white rounded-xl shadow-sm border border-slate-200 flex flex-col h-full overflow-hidden">
                    
                    <!-- Search Bar Toolbar -->
                    <div class="p-3 bg-slate-50 border-b border-slate-200 flex items-center gap-3">
                        <span class="text-slate-400">🔍</span>
                        <input type="text" id="searchInput" onkeyup="filterTable()" placeholder="Search processed items..." 
                               class="w-full bg-transparent focus:outline-none text-sm font-semibold text-slate-700">
                    </div>

                    <div class="overflow-y-auto flex-grow relative">
                        <table class="w-full text-left border-collapse" id="inventoryTable">
                            <thead class="sticky top-0 bg-slate-100 shadow-sm z-20">
                                <tr class="text-slate-600 text-xs uppercase tracking-wider border-b">
                                    <th class="p-4 font-bold">Raw Input</th>
                                    <th class="p-4 font-bold">Clean Name <span class="text-[10px] text-blue-500 normal-case">(Click to Edit)</span></th>
                                    <th class="p-4 font-bold">Category</th>
                                    <th class="p-4 font-bold">Weight</th>
                                    <th class="p-4 font-bold">Confidence</th>
                                </tr>
                            </thead>
                            <tbody id="tableBody" class="divide-y divide-slate-100">
                                <!-- JS will populate this -->
                            </tbody>
                        </table>
                        <div id="emptyState" class="p-12 text-center text-slate-400 text-sm absolute inset-0 flex flex-col items-center justify-center pointer-events-none">
                            <div class="text-5xl mb-4 opacity-50">🤖</div>
                            Waiting for messy data...
                        </div>
                    </div>
                </div>
            </div>
        </div>

        <script>
            let inventoryData = [];

            const messyDatabase = [
                "amul pnner 200", "hrpic bth clean 500ml", "mdh chana msl 100gm pk",
                "srf xl matic 1kg", "tata namak 1 kg free", "brtnnia mr gld 250g",
                "dbr rd pst 100", "pntnjli dnt kanti 200g", "clgt mx frsh 150g",
                "mgi 2min ndl 70g", "kt kt choco 38g", "lsy pot chips 50g bl magic",
                "kissan mx frt jam 500g", "vivel sbp 100g pnk", "fortune snflwr oil 1l"
            ];

            function generateRandomItems() {
                let count = parseInt(document.getElementById('testCount').value) || 6;
                const shuffled = [...messyDatabase].sort(() => 0.5 - Math.random());
                document.getElementById('rawName').value = shuffled.slice(0, count).join('\\n');
            }

            function clearAll() {
                inventoryData = [];
                document.getElementById('tableBody').innerHTML = '';
                document.getElementById('emptyState').style.display = 'flex';
                document.getElementById('rawName').value = '';
                updateStats();
            }

            function updateStats() {
                document.getElementById('statTotal').innerText = inventoryData.length;
                const reviewCount = inventoryData.filter(item => item.confidence < 85 || item.clean === "Requires Manual Entry").length;
                document.getElementById('statReview').innerText = reviewCount;
            }

            // HITL: Update underlying data when user edits the table cell
            function editCell(index, key, element) {
                inventoryData[index][key] = element.innerText.trim();
                element.classList.add('bg-green-50', 'text-green-800');
                setTimeout(() => element.classList.remove('bg-green-50', 'text-green-800'), 1000);
                updateStats();
            }

            // Search filter function
            function filterTable() {
                const input = document.getElementById("searchInput").value.toUpperCase();
                const trs = document.getElementById("tableBody").getElementsByTagName("tr");
                for (let i = 0; i < trs.length; i++) {
                    const txtValue = trs[i].textContent || trs[i].innerText;
                    trs[i].style.display = txtValue.toUpperCase().indexOf(input) > -1 ? "" : "none";
                }
            }

            async function categorize() {
                const rawText = document.getElementById('rawName').value.trim();
                const btn = document.getElementById('submitBtn');
                if(!rawText) return;

                const lines = rawText.split('\\n').filter(line => line.trim() !== '');
                btn.classList.add('opacity-75', 'cursor-not-allowed');
                btn.disabled = true;
                document.getElementById('emptyState').style.display = 'none';
                
                for (let i = 0; i < lines.length; i++) {
                    const line = lines[i];
                    btn.innerHTML = `Processing (${i + 1}/${lines.length})...`;
                    
                    try {
                        const response = await fetch('/categorize', {
                            method: 'POST',
                            headers: { 'Content-Type': 'application/json' },
                            body: JSON.stringify({ raw_name: line })
                        });
                        
                        const data = await response.json();
                        
                        inventoryData.push({
                            raw: line,
                            clean: data.clean_name,
                            category: data.category,
                            weight: data.weight_volume,
                            confidence: data.confidence,
                            reasoning: data.reasoning
                        });
                        
                        updateTable(inventoryData.length - 1);
                        updateStats();
                    } catch (err) {
                        console.error("Failed to process:", line);
                    }
                }

                btn.innerHTML = "Process Batch";
                btn.classList.remove('opacity-75', 'cursor-not-allowed');
                btn.disabled = false;
                document.getElementById('rawName').value = ''; 
            }

            function updateTable(index) {
                const tbody = document.getElementById('tableBody');
                const item = inventoryData[index];
                
                const needsReview = item.confidence < 85 || item.clean === "Requires Manual Entry";
                const color = item.confidence > 90 ? 'bg-emerald-500' : (needsReview ? 'bg-red-500' : 'bg-amber-400');
                const reviewBadge = needsReview ? `<span class="ml-2 text-[10px] bg-red-100 text-red-700 px-2 py-0.5 rounded-full border border-red-200 uppercase font-bold">⚠️ Review</span>` : '';
                
                const row = document.createElement('tr');
                row.className = needsReview ? "bg-red-50/20 hover:bg-slate-50 transition animate-fade-in" : "hover:bg-slate-50 transition animate-fade-in";
                
                row.innerHTML = `
                    <td class="p-4 text-sm font-mono text-slate-500">${item.raw}</td>
                    
                    <!-- EDITABLE CELL WITH XAI HOVER -->
                    <td class="p-4 text-sm font-bold text-slate-800">
                        <div class="flex items-center">
                            <div class="group relative flex items-center cursor-help mr-2">
                                <span class="opacity-50">🧠</span>
                                <div class="invisible group-hover:visible absolute left-0 bottom-full mb-2 w-64 p-3 bg-slate-800 text-white text-xs rounded-lg shadow-xl z-50 border border-slate-700">
                                    <span class="block font-bold text-emerald-400 mb-1">AI Thought Process:</span>
                                    ${item.reasoning}
                                </div>
                            </div>
                            <span contenteditable="true" onblur="editCell(${index}, 'clean', this)" 
                                  class="outline-none focus:bg-white focus:ring-2 focus:ring-blue-400 rounded px-1 transition cursor-text border-b border-dashed border-slate-300">
                                ${item.clean}
                            </span>
                            ${reviewBadge}
                        </div>
                    </td>

                    <td class="p-4"><span contenteditable="true" onblur="editCell(${index}, 'category', this)" class="px-3 py-1 bg-indigo-50 text-indigo-700 rounded-md text-xs font-bold border border-indigo-100 outline-none focus:ring-2 cursor-text">${item.category}</span></td>
                    <td class="p-4 text-sm font-semibold text-slate-600"><span contenteditable="true" onblur="editCell(${index}, 'weight', this)" class="outline-none focus:ring-2 cursor-text border-b border-dashed border-slate-300 px-1">${item.weight}</span></td>
                    <td class="p-4">
                        <div class="flex items-center gap-2">
                            <div class="w-16 bg-slate-200 rounded-full h-1.5 overflow-hidden">
                                <div class="${color} h-1.5 rounded-full transition-all duration-1000" style="width: ${item.confidence}%"></div>
                            </div>
                            <span class="text-xs font-bold text-slate-500">${item.confidence}%</span>
                        </div>
                    </td>
                `;
                tbody.insertBefore(row, tbody.firstChild);
            }

            function downloadCSV() {
                if(inventoryData.length === 0) return alert("No data to export!");
                let csv = "Raw Name,Clean Name,Category,Weight/Volume,AI Confidence,AI Reasoning\\n";
                inventoryData.forEach(row => {
                    csv += `"${row.raw}","${row.clean}","${row.category}","${row.weight}","${row.confidence}","${row.reasoning}"\\n`;
                });
                const link = document.createElement("a");
                link.href = encodeURI("data:text/csv;charset=utf-8," + csv);
                link.download = "ai_inventory_export.csv";
                document.body.appendChild(link); link.click(); link.remove();
            }
        </script>
        <style>
            @keyframes fadeIn { from { opacity: 0; transform: translateY(-5px); } to { opacity: 1; transform: translateY(0); } }
            .animate-fade-in { animation: fadeIn 0.3s ease-out forwards; }
            ::-webkit-scrollbar { width: 8px; }
            ::-webkit-scrollbar-track { background: #f1f5f9; }
            ::-webkit-scrollbar-thumb { background: #cbd5e1; border-radius: 4px; }
        </style>
    </body>
    </html>
    """
    return HTMLResponse(content=html_content)

@app.post("/categorize")
def categorize_item(item: InventoryItem):
    system_prompt = """
    You are an expert Indian FMCG data parser. 
    Analyze the raw shorthand text, fix typos, and strictly assign a category.
    
    INDIAN FMCG DICTIONARY (USE THIS TO DECODE):
    - pntnjli dnt kanti = Patanjali Dant Kanti (Oral Care)
    - lsy pot chips = Lays Potato Chips (Snacks)
    - brtnnia mr gld = Britannia Marie Gold (Snacks)
    - dbr rd pst = Dabur Red Paste (Oral Care)
    - mgi 2min ndl = Maggi 2-Minute Noodles (Food)
    - tata namak = Tata Salt (Food)
    - fortune snflwr = Fortune Sunflower Oil (Food)
    - clgt = Colgate (Oral Care)
    - hrpic = Harpic (Cleaning)
    - vivel sbp = Vivel Soap (Personal Care)
    - kissan mx frt jam = Kissan Mixed Fruit Jam (Food)
    
    ALLOWED CATEGORIES:
    Spices, Dairy, Cleaning, Oral Care, Personal Care, Snacks, Food, Beverages, Unknown.

    You MUST return ONLY a valid JSON object with exactly these FIVE keys:
    "reasoning" (string: explain the abbreviation using the dictionary),
    "clean_name" (string: properly spelled brand and product name), 
    "category" (string: MUST be one of the ALLOWED CATEGORIES), 
    "weight_volume" (string: extract pack size. Return 'N/A' if none),
    "confidence" (integer: 1-100).
    
    EXAMPLES TO LEARN FROM:
    Input: "clgt mx frsh 150g"
    Output: {"reasoning": "clgt is Colgate.", "clean_name": "Colgate Max Fresh", "category": "Oral Care", "weight_volume": "150g", "confidence": 99}

    Input: "srf xl matic 1kg"
    Output: {"reasoning": "srf xl is Surf Excel.", "clean_name": "Surf Excel Matic", "category": "Cleaning", "weight_volume": "1kg", "confidence": 98}
    
    Input: "mdh chana msl 100gm pk"
    Output: {"reasoning": "msl is Masala.", "clean_name": "MDH Chana Masala", "category": "Spices", "weight_volume": "100g", "confidence": 98}
    """
    
    try:
        response = ollama.chat(
            model='llama3.2:1b',
            format='json',
            messages=[
                {'role': 'system', 'content': system_prompt},
                {'role': 'user', 'content': f"Categorize this: {item.raw_name}"}
            ]
        )
        
        raw_json = json.loads(response['message']['content'])
        
        safe_data = {
            "reasoning": raw_json.get("reasoning", "Decoded using dictionary."),
            "clean_name": raw_json.get("clean_name", raw_json.get("cleanName", raw_json.get("name", "Requires Manual Entry"))),
            "category": raw_json.get("category", "Unknown"),
            "weight_volume": raw_json.get("weight_volume", raw_json.get("weight", "N/A")),
            "confidence": raw_json.get("confidence", 0)
        }
        
        return safe_data
        
    except Exception:
        return {
            "reasoning": "AI completely failed to process this string.",
            "clean_name": "Requires Manual Entry",
            "category": "Unknown",
            "weight_volume": "N/A",
            "confidence": 0
        }