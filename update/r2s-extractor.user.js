// ==UserScript==
// @name        R2S Video Info Extractor
// @description Extract Bilibili Touhou video info (Author, Source, Title, URL) for R2S spreadsheet
// @match       https://www.bilibili.com/video/*
// @grant       GM_xmlhttpRequest
// @connect     www.youtube.com
// @connect     www.nicovideo.jp
// @connect     nico.ms
// @run-at      document-idle
// ==/UserScript==

(function () {
    'use strict';

    // ── Extract info from the current Bilibili page ──────────────────────────
    function getBilibiliInfo() {
        const title = document.title
            .replace(/_哔哩哔哩_bilibili|_哔哩哔哩|_bilibili/g, '')
            .trim();

        let desc = '';
        const descElem = document.querySelector("meta[name='description']");
        if (descElem) desc = descElem.getAttribute('content');

        const urlMatch = desc.match(
            /https?:\/\/(?:(?:www|m)\.youtube\.com\/watch\?v=[A-Za-z0-9_\-]{11}|youtu\.be\/[A-Za-z0-9_\-]{11}|(?:www\.)?nicovideo\.jp\/watch\/[a-zA-Z]{2}\d+|nico\.ms\/[a-zA-Z]{2}\d+)/
        );
        const idMatch = desc.match(/([a-zA-Z]{2}\d+)/);

        let sourceUrl = '';
        if (urlMatch) {
            sourceUrl = urlMatch[0];
        } else if (idMatch) {
            sourceUrl = `https://www.nicovideo.jp/watch/${idMatch[1]}`;
        }

        const rawUrl = window.location.href;
        const bvMatch = rawUrl.match(/(https?:\/\/[^/]+\/video\/[A-Za-z0-9]+)/);
        const url = bvMatch ? bvMatch[1] : rawUrl;

        return { title, desc: sourceUrl || 'Not Found', url, sourceUrl };
    }

    // ── Cross-origin fetch via GM_xmlhttpRequest ─────────────────────────────
    function gmFetch(url) {
        return new Promise((resolve, reject) => {
            GM_xmlhttpRequest({
                method: 'GET',
                url,
                onload(resp) {
                    resolve({
                        ok: resp.status >= 200 && resp.status < 300,
                        text() { return resp.responseText; },
                        json() { return JSON.parse(resp.responseText); },
                    });
                },
                onerror: reject,
                ontimeout: reject,
            });
        });
    }

    // ── Fetch original author from YouTube / NicoNico ────────────────────────
    async function getAuthor(sourceUrl) {
        if (!sourceUrl) return 'Not Found';
        try {
            if (sourceUrl.includes('youtube.com') || sourceUrl.includes('youtu.be')) {
                const resp = await gmFetch(
                    `https://www.youtube.com/oembed?url=${encodeURIComponent(sourceUrl)}&format=json`
                );
                if (resp.ok) {
                    const data = resp.json();
                    return data.author_name || 'Not Found';
                }
            }

            if (sourceUrl.includes('nicovideo.jp') || sourceUrl.includes('nico.ms')) {
                const resp = await gmFetch(sourceUrl);
                if (resp.ok) {
                    const html = resp.text();
                    // Try JSON-LD block first
                    const jsonLdBlocks = html.match(
                        /<script[^>]*type="application\/ld\+json"[^>]*>[\s\S]*?<\/script>/g
                    );
                    if (jsonLdBlocks) {
                        for (const block of jsonLdBlocks) {
                            const content = block
                                .replace(/<script[^>]*>/, '')
                                .replace(/<\/script>/, '')
                                .trim()
                                .replace(/&#34;/g, '"')
                                .replace(/&amp;/g, '&')
                                .replace(/&lt;/g, '<')
                                .replace(/&gt;/g, '>')
                                .replace(/&quot;/g, '"')
                                .replace(/&#39;/g, "'");
                            try {
                                const json = JSON.parse(content);
                                if (
                                    json['@type'] === 'VideoObject' &&
                                    json.author &&
                                    json.author.name
                                ) {
                                    return json.author.name;
                                }
                            } catch (_) { continue; }
                        }
                    }
                    // Fallback: nickname field in server-rendered HTML
                    const nickMatch = html.match(/"nickname"\s*:\s*"([^"]+)"/);
                    if (nickMatch && nickMatch[1]) return nickMatch[1];
                }
            }
        } catch (e) {
            console.error('[R2S] getAuthor error:', e);
        }
        return 'Not Found';
    }

    // ── Build floating panel UI ──────────────────────────────────────────────
    function createPanel() {
        const panel = document.createElement('div');
        panel.id = 'r2s-panel';
        panel.style.cssText = `
            position: fixed;
            top: 60px;
            right: 20px;
            z-index: 2147483647;
            background: #fff;
            border: 1px solid #ccc;
            border-radius: 8px;
            box-shadow: 0 4px 16px rgba(0,0,0,0.18);
            padding: 14px 16px 12px;
            font-family: sans-serif;
            font-size: 13px;
            min-width: 340px;
            max-width: 600px;
        `;

        panel.innerHTML = `
            <div style="display:flex;align-items:center;justify-content:space-between;margin-bottom:10px;">
                <b style="font-size:14px;">R2S 信息提取器</b>
                <button id="r2s-close" style="
                    border:none;background:none;font-size:18px;cursor:pointer;
                    line-height:1;color:#888;padding:0 4px;
                ">×</button>
            </div>
            <div style="font-size:12px;color:#555;background:#f5f5f5;border:1px solid #ddd;
                        border-radius:4px;padding:6px 10px;margin-bottom:10px;line-height:1.8;">
                支持原视频为 <b>油管 (YouTube)</b> 和 <b>N站 (NicoNico)</b> 的 B 站投稿。<br>
                作者名需联网获取，稍等片刻。点击 <b>Copy</b> 将 Tab 分隔数据复制至剪贴板。
            </div>
            <div id="r2s-info"></div>
        `;

        document.body.appendChild(panel);

        document.getElementById('r2s-close').addEventListener('click', () => panel.remove());
        return panel;
    }

    function showResultTable(panel, res, author) {
        const infoDiv = panel.querySelector('#r2s-info');

        // Build a simple table
        const table = document.createElement('table');
        table.style.cssText = 'border-collapse:collapse;width:100%;font-size:12px;';

        const headers = ['Author', 'Source', 'Title', 'URL', 'Translation'];
        const thead = document.createElement('thead');
        const headerRow = document.createElement('tr');
        headers.forEach(h => {
            const th = document.createElement('th');
            th.textContent = h;
            th.style.cssText = 'border:1px solid #ccc;padding:4px 8px;background:#f0f0f0;white-space:nowrap;';
            headerRow.appendChild(th);
        });
        thead.appendChild(headerRow);
        table.appendChild(thead);

        const tbody = document.createElement('tbody');
        const dataRow = document.createElement('tr');

        const authorCell = document.createElement('td');
        authorCell.textContent = author;
        authorCell.style.cssText = 'border:1px solid #ccc;padding:4px 8px;';

        const sourceCell = document.createElement('td');
        sourceCell.style.cssText = 'border:1px solid #ccc;padding:4px 8px;word-break:break-all;';
        if (res.desc !== 'Not Found') {
            const a = document.createElement('a');
            a.href = res.desc;
            a.textContent = res.desc;
            a.target = '_blank';
            a.rel = 'noopener';
            sourceCell.appendChild(a);
        } else {
            sourceCell.textContent = 'Not Found';
        }

        const titleCell = document.createElement('td');
        titleCell.textContent = res.title;
        titleCell.style.cssText = 'border:1px solid #ccc;padding:4px 8px;';

        const urlCell = document.createElement('td');
        urlCell.style.cssText = 'border:1px solid #ccc;padding:4px 8px;word-break:break-all;';
        const urlA = document.createElement('a');
        urlA.href = res.url;
        urlA.textContent = res.url;
        urlA.target = '_blank';
        urlA.rel = 'noopener';
        urlCell.appendChild(urlA);

        const transCell = document.createElement('td');
        transCell.style.cssText = 'border:1px solid #ccc;padding:4px 8px;';
        const transInput = document.createElement('input');
        transInput.type = 'number';
        transInput.id = 'r2s-translation';
        transInput.value = '1';
        transInput.style.cssText = 'width:50px;';
        transCell.appendChild(transInput);

        [authorCell, sourceCell, titleCell, urlCell, transCell].forEach(c => dataRow.appendChild(c));
        tbody.appendChild(dataRow);
        table.appendChild(tbody);

        const copyBtn = document.createElement('button');
        copyBtn.textContent = 'Copy';
        copyBtn.style.cssText = 'margin-top:8px;padding:4px 16px;cursor:pointer;';
        copyBtn.addEventListener('click', () => {
            const translation = document.getElementById('r2s-translation').value;
            const currentAuthor = authorCell.textContent; // read live value from DOM
            const text = `${currentAuthor}\t${res.desc}\t${res.title}\t${res.url}\t${translation}`;
            navigator.clipboard.writeText(text).then(() => {
                const tip = document.createElement('div');
                tip.textContent = '复制成功！';
                tip.style.cssText = `
                    position:fixed;top:20px;left:50%;transform:translateX(-50%);
                    background:rgba(60,180,80,0.95);color:#fff;padding:8px 24px;
                    border-radius:6px;font-size:15px;z-index:2147483647;
                `;
                document.body.appendChild(tip);
                setTimeout(() => tip.remove(), 2000);
            });
        });

        infoDiv.innerHTML = '';
        infoDiv.appendChild(table);
        infoDiv.appendChild(copyBtn);
    }

    // ── Floating trigger button ──────────────────────────────────────────────
    function addTriggerButton() {
        const btn = document.createElement('button');
        btn.textContent = 'R2S';
        btn.title = 'R2S Video Info Extractor';
        btn.style.cssText = `
            position: fixed;
            bottom: 80px;
            right: 20px;
            z-index: 2147483646;
            background: #00a1d6;
            color: #fff;
            border: none;
            border-radius: 50%;
            width: 48px;
            height: 48px;
            font-size: 13px;
            font-weight: bold;
            cursor: pointer;
            box-shadow: 0 2px 8px rgba(0,0,0,0.25);
        `;

        btn.addEventListener('click', async () => {
            // Remove existing panel if open
            const existing = document.getElementById('r2s-panel');
            if (existing) { existing.remove(); return; }

            const panel = createPanel();
            const infoDiv = panel.querySelector('#r2s-info');
            infoDiv.textContent = '正在提取信息…';

            const res = getBilibiliInfo();

            // Render table immediately with "Loading..." for author
            showResultTable(panel, res, 'Loading...');

            // Fetch author asynchronously
            const author = await getAuthor(res.sourceUrl);
            const authorCells = panel.querySelectorAll('tbody td');
            if (authorCells.length > 0) authorCells[0].textContent = author;
        });

        document.body.appendChild(btn);
    }

    // Wait until page body is ready, then inject
    if (document.body) {
        addTriggerButton();
    } else {
        window.addEventListener('DOMContentLoaded', addTriggerButton);
    }
})();
