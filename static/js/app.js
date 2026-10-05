/**
 * AP News English Lab - Frontend Client Logic
 */

document.addEventListener('DOMContentLoaded', () => {
    // State management
    const state = {
        currentCategory: 'top',
        currentUrl: 'https://apnews.com/',
        articles: [],
        translations: {},      // articleId -> translation string
        wordAnalyses: {},      // articleId -> word analysis array
        summaries: {},         // articleId -> summary text
        currentPlayingId: null, // currently playing article/word ID
        theme: localStorage.getItem('apnews_theme') || 'dark'
    };

    // DOM Elements
    const connectionBadge = document.getElementById('connectionBadge');
    const articlesList = document.getElementById('articlesList');
    const loadingState = document.getElementById('loadingState');
    const currentCategoryTitle = document.getElementById('currentCategoryTitle');
    const feedSourceText = document.getElementById('feedSourceText');
    const articleCount = document.getElementById('articleCount');
    const cacheTimePill = document.getElementById('cacheTimePill');
    const btnRefresh = document.getElementById('btnRefresh');
    const btnThemeToggle = document.getElementById('btnThemeToggle');
    const catPills = document.querySelectorAll('.cat-pill');
    const globalAudioPlayer = document.getElementById('globalAudioPlayer');

    // Quick URL Bar Elements
    const customUrlInput = document.getElementById('customUrlInput');
    const btnCheckInputUrl = document.getElementById('btnCheckInputUrl');
    const btnLoadCustomUrl = document.getElementById('btnLoadCustomUrl');
    const urlQuickResult = document.getElementById('urlQuickResult');

    // Modal Elements
    const btnUrlModal = document.getElementById('btnUrlModal');
    const urlModal = document.getElementById('urlModal');
    const btnCloseModal = document.getElementById('btnCloseModal');
    const btnCloseModalBottom = document.getElementById('btnCloseModalBottom');
    const checkModalUrl = document.getElementById('checkModalUrl');
    const btnRunModalCheck = document.getElementById('btnRunModalCheck');
    const modalCheckResult = document.getElementById('modalCheckResult');
    const btnApplyModalUrl = document.getElementById('btnApplyModalUrl');
    const presetBtns = document.querySelectorAll('.preset-btn');

    // Status Elements
    const statArticles = document.getElementById('statArticles');
    const statTrans = document.getElementById('statTrans');
    const statAnalyses = document.getElementById('statAnalyses');
    const statSummaries = document.getElementById('statSummaries');

    // ==========================================
    // Theme Management
    // ==========================================
    function applyTheme(theme) {
        document.documentElement.setAttribute('data-theme', theme);
        localStorage.setItem('apnews_theme', theme);
        const icon = btnThemeToggle.querySelector('i');
        if (theme === 'light') {
            icon.className = 'fa-solid fa-sun';
        } else {
            icon.className = 'fa-solid fa-moon';
        }
    }
    applyTheme(state.theme);

    btnThemeToggle.addEventListener('click', () => {
        state.theme = state.theme === 'dark' ? 'light' : 'dark';
        applyTheme(state.theme);
    });

    // ==========================================
    // Audio Player Management
    // ==========================================
    function playAudio(text, btnElement, playId) {
        if (state.currentPlayingId === playId && !globalAudioPlayer.paused) {
            globalAudioPlayer.pause();
            btnElement.classList.remove('playing');
            state.currentPlayingId = null;
            return;
        }

        // Reset previous playing button
        document.querySelectorAll('.action-btn.playing, .word-tts-btn.playing').forEach(el => {
            el.classList.remove('playing');
        });

        btnElement.classList.add('playing');
        state.currentPlayingId = playId;

        const encoded = encodeURIComponent(text);
        globalAudioPlayer.src = `/api/tts?text=${encoded}`;
        globalAudioPlayer.play().catch(err => {
            console.error('Audio play error:', err);
            btnElement.classList.remove('playing');
            state.currentPlayingId = null;
        });

        globalAudioPlayer.onended = () => {
            btnElement.classList.remove('playing');
            state.currentPlayingId = null;
        };

        globalAudioPlayer.onerror = () => {
            btnElement.classList.remove('playing');
            state.currentPlayingId = null;
        };
    }

    // ==========================================
    // News Fetching & Rendering
    // ==========================================
    async function loadNews(category = 'top', customUrl = '', refresh = false) {
        articlesList.innerHTML = `
            <div class="loading-state">
                <div class="spinner"></div>
                <p class="loading-text">AP News 최신 기사를 수집하고 있습니다...</p>
            </div>
        `;

        try {
            let url = `/api/news?category=${category}&refresh=${refresh}`;
            if (customUrl) {
                url += `&url=${encodeURIComponent(customUrl)}`;
            }

            const res = await fetch(url);
            const data = await res.json();

            if (data.status === 'success' && data.articles) {
                state.articles = data.articles;
                articleCount.textContent = data.articles.length;
                feedSourceText.textContent = `출처: ${data.source}`;
                cacheTimePill.innerHTML = `<i class="fa-regular fa-clock"></i> ${data.timestamp.split(' ')[1]}`;
                
                // Update connection badge
                updateConnectionStatus('online', data.source);
                renderArticles(data.articles);
                updateStats();
            } else {
                renderError('기사를 가져오지 못했습니다. URL을 확인해 주세요.');
            }
        } catch (err) {
            console.error('Load news error:', err);
            renderError('네트워크 오류가 발생했습니다. 잠시 후 다시 시도해 주세요.');
            updateConnectionStatus('error', '서버 통신 실패');
        }
    }

    function renderArticles(articles) {
        if (!articles || articles.length === 0) {
            articlesList.innerHTML = `
                <div class="loading-state">
                    <i class="fa-solid fa-circle-exclamation" style="font-size: 2.5rem; color: var(--warning); margin-bottom: 12px;"></i>
                    <p class="loading-text">가져온 기사가 없습니다. 다른 카테고리나 URL을 선택해 보세요.</p>
                </div>
            `;
            return;
        }

        articlesList.innerHTML = '';
        articles.forEach(art => {
            const card = document.createElement('article');
            card.className = 'article-card';
            card.id = `art-card-${art.id}`;

            let cleanDesc = (art.description || '').trim();
            if (!cleanDesc || cleanDesc.includes('<a') || cleanDesc.endsWith('AP News') || cleanDesc.endsWith('apnews.com') || cleanDesc.toLowerCase().includes((art.title || '').toLowerCase().slice(0, 25))) {
                cleanDesc = '';
            }
            const descHtml = cleanDesc ? `<p class="article-desc">${escapeHtml(cleanDesc)}</p>` : '';
            const linkHtml = art.link ? `
                <a href="${art.link}" target="_blank" rel="noopener noreferrer" class="article-link" title="AP News 원문 기사 열기">
                    <span>AP News 원문</span>
                    <i class="fa-solid fa-arrow-up-right-from-square"></i>
                </a>
            ` : '';

            card.innerHTML = `
                <div class="article-header">
                    <span class="article-badge"><i class="fa-regular fa-newspaper"></i> 기사 #${art.id}</span>
                    ${linkHtml}
                </div>
                <h2 class="article-headline">${escapeHtml(art.title)}</h2>
                ${descHtml}
                <div class="article-actions">
                    <button class="action-btn btn-tts" data-id="${art.id}">
                        <i class="fa-solid fa-volume-high"></i>
                        <span>🔊 읽기</span>
                    </button>
                    <button class="action-btn btn-translate" data-id="${art.id}">
                        <i class="fa-solid fa-language"></i>
                        <span>🇰🇷 번역</span>
                    </button>
                    <button class="action-btn btn-analyze" data-id="${art.id}">
                        <i class="fa-solid fa-book-open"></i>
                        <span>📚 단어 분석</span>
                    </button>
                    <button class="action-btn btn-summary" data-id="${art.id}" data-url="${art.link}" data-title="${escapeHtml(art.title)}">
                        <i class="fa-solid fa-list-check"></i>
                        <span>📝 요약본</span>
                    </button>
                </div>
                <div class="translation-panel hidden" id="trans-panel-${art.id}"></div>
                <div class="analysis-panel hidden" id="analysis-panel-${art.id}"></div>
                <div class="summary-panel hidden" id="summary-panel-${art.id}"></div>
            `;

            // Event Listeners for Actions
            const btnTts = card.querySelector('.btn-tts');
            btnTts.addEventListener('click', () => {
                playAudio(art.title, btnTts, `art-${art.id}`);
            });

            const btnTranslate = card.querySelector('.btn-translate');
            btnTranslate.addEventListener('click', () => {
                toggleTranslation(art.id, art.title, btnTranslate);
            });

            const btnAnalyze = card.querySelector('.btn-analyze');
            btnAnalyze.addEventListener('click', () => {
                toggleWordAnalysis(art.id, art.title, btnAnalyze);
            });

            const btnSummary = card.querySelector('.btn-summary');
            btnSummary.addEventListener('click', () => {
                toggleSummary(art.id, btnSummary.getAttribute('data-url'), btnSummary.getAttribute('data-title'), btnSummary);
            });

            articlesList.appendChild(card);
        });
    }

    function renderError(message) {
        articlesList.innerHTML = `
            <div class="loading-state">
                <i class="fa-solid fa-triangle-exclamation" style="font-size: 2.5rem; color: var(--danger); margin-bottom: 12px;"></i>
                <p class="loading-text">${escapeHtml(message)}</p>
                <button class="btn btn-outline" style="margin-top: 16px;" onclick="location.reload()">
                    <i class="fa-solid fa-rotate-right"></i> 다시 시도
                </button>
            </div>
        `;
    }

    // ==========================================
    // Translation Logic
    // ==========================================
    async function toggleTranslation(id, text, button) {
        const panel = document.getElementById(`trans-panel-${id}`);
        if (!panel.classList.contains('hidden')) {
            panel.classList.add('hidden');
            button.classList.remove('active');
            return;
        }

        button.classList.add('active');
        panel.classList.remove('hidden');

        // Check client cache
        if (state.translations[id]) {
            renderTranslationContent(panel, state.translations[id]);
            return;
        }

        panel.innerHTML = `<p style="color: var(--text-muted); font-size: 0.88rem;"><i class="fa-solid fa-spinner fa-spin"></i> 한글 번역 생성 중...</p>`;

        try {
            const res = await fetch('/api/translate', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ text })
            });
            const data = await res.json();

            if (data.status === 'success') {
                state.translations[id] = data.translation;
                renderTranslationContent(panel, data.translation);
                updateStats();
            } else {
                panel.innerHTML = `<p style="color: var(--danger);">번역 실패: ${data.message || '오류 발생'}</p>`;
            }
        } catch (err) {
            panel.innerHTML = `<p style="color: var(--danger);">번역 요청 중 네트워크 오류가 발생했습니다.</p>`;
        }
    }

    function renderTranslationContent(panel, translation) {
        panel.innerHTML = `
            <div class="trans-label"><i class="fa-solid fa-language"></i> 한글 번역</div>
            <div class="trans-content">${escapeHtml(translation)}</div>
        `;
    }

    // ==========================================
    // Word Analysis Logic
    // ==========================================
    async function toggleWordAnalysis(id, text, button) {
        const panel = document.getElementById(`analysis-panel-${id}`);
        if (!panel.classList.contains('hidden')) {
            panel.classList.add('hidden');
            button.classList.remove('active');
            return;
        }

        button.classList.add('active');
        panel.classList.remove('hidden');

        // Check client cache
        if (state.wordAnalyses[id]) {
            renderWordAnalysisContent(panel, state.wordAnalyses[id]);
            return;
        }

        panel.innerHTML = `<p style="color: var(--text-muted); font-size: 0.88rem;"><i class="fa-solid fa-spinner fa-spin"></i> 문장 내 단어 및 발음기호 분석 중...</p>`;

        try {
            const res = await fetch('/api/analyze', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ text })
            });
            const data = await res.json();

            if (data.status === 'success' && data.words) {
                state.wordAnalyses[id] = data.words;
                renderWordAnalysisContent(panel, data.words);
                updateStats();
            } else {
                panel.innerHTML = `<p style="color: var(--danger);">단어 분석 실패: ${data.message || '오류 발생'}</p>`;
            }
        } catch (err) {
            panel.innerHTML = `<p style="color: var(--danger);">단어 분석 요청 중 네트워크 오류가 발생했습니다.</p>`;
        }
    }

    function renderWordAnalysisContent(panel, words) {
        if (!words || words.length === 0) {
            panel.innerHTML = `<p style="color: var(--text-muted);">분석할 주요 단어가 없습니다.</p>`;
            return;
        }

        let tableRows = words.map(w => {
            const posClass = w.pos || '기타';
            return `
                <tr>
                    <td>
                        <div class="word-cell">
                            <span>${escapeHtml(w.word)}</span>
                            <button class="word-tts-btn" title="${w.word} 발음 듣기" data-word="${escapeHtml(w.word)}">
                                <i class="fa-solid fa-volume-low"></i>
                            </button>
                        </div>
                    </td>
                    <td><span class="ipa-text">${escapeHtml(w.ipa)}</span></td>
                    <td><span class="pos-badge ${posClass}">${escapeHtml(w.pos)}</span></td>
                    <td class="meaning-cell">${escapeHtml(w.meaning)}</td>
                </tr>
            `;
        }).join('');

        panel.innerHTML = `
            <div class="analysis-header">
                <span class="analysis-title"><i class="fa-solid fa-book-open-reader"></i> 단어별 발음기호(IPA) 및 사전 뜻</span>
                <span style="font-size: 0.8rem; color: var(--text-muted);">${words.length}개 단어</span>
            </div>
            <div class="word-table-container">
                <table class="word-table">
                    <thead>
                        <tr>
                            <th style="width: 25%;">단어</th>
                            <th style="width: 25%;">발음기호 (IPA)</th>
                            <th style="width: 15%;">품사</th>
                            <th style="width: 35%;">뜻 (WordNet)</th>
                        </tr>
                    </thead>
                    <tbody>
                        ${tableRows}
                    </tbody>
                </table>
            </div>
        `;

        // Attach event listeners to word audio buttons
        panel.querySelectorAll('.word-tts-btn').forEach(btn => {
            btn.addEventListener('click', (e) => {
                e.stopPropagation();
                const word = btn.getAttribute('data-word');
                playAudio(word, btn, `word-${word}`);
            });
        });
    }

    // ==========================================
    // Summary Logic
    // ==========================================
    async function toggleSummary(id, url, title, button) {
        if (!url) {
            alert('기사 원문 링크가 없어 요약할 수 없습니다.');
            return;
        }

        const panel = document.getElementById(`summary-panel-${id}`);
        if (!panel.classList.contains('hidden')) {
            panel.classList.add('hidden');
            button.classList.remove('active');
            return;
        }

        button.classList.add('active');
        panel.classList.remove('hidden');

        // Check client cache
        if (state.summaries[id]) {
            renderSummaryContent(panel, state.summaries[id], id);
            return;
        }

        panel.innerHTML = `<p style="color: var(--text-muted); font-size: 0.88rem;"><i class="fa-solid fa-spinner fa-spin"></i> 원문 기사를 크롤링하여 요약하는 중입니다 (최대 15초 소요)...</p>`;

        try {
            const titleParam = title ? `&title=${encodeURIComponent(title)}` : '';
            const res = await fetch(`/api/summary?url=${encodeURIComponent(url)}${titleParam}`);
            const data = await res.json();

            if (data.status === 'success') {
                state.summaries[id] = data.summary;
                renderSummaryContent(panel, data.summary, id);
                updateStats();
            } else {
                panel.innerHTML = `<p style="color: var(--danger);">요약 실패: ${data.message || '오류 발생'}</p>`;
            }
        } catch (err) {
            panel.innerHTML = `<p style="color: var(--danger);">네트워크 오류가 발생했습니다.</p>`;
        }
    }

    function renderSummaryContent(panel, summary, id) {
        panel.innerHTML = `
            <div class="summary-header" style="display:flex; justify-content:space-between; align-items:center; margin-bottom: 12px; border-bottom: 1px solid var(--border-color); padding-bottom: 8px;">
                <span class="summary-title" style="font-weight: 600; color: var(--accent);"><i class="fa-solid fa-file-lines"></i> 원문 핵심 요약</span>
                <div class="summary-actions">
                    <button class="btn btn-sm btn-outline sum-tts-btn" style="margin-right: 8px;"><i class="fa-solid fa-volume-high"></i> 요약 듣기</button>
                    <button class="btn btn-sm btn-outline sum-trans-btn"><i class="fa-solid fa-language"></i> 한글 번역</button>
                </div>
            </div>
            <div class="summary-text" style="line-height: 1.6; color: var(--text-color); margin-bottom: 12px;">${escapeHtml(summary)}</div>
            <div class="summary-trans-text hidden" style="line-height: 1.6; color: var(--text-color); padding: 12px; background: rgba(59, 130, 246, 0.1); border-radius: 8px;"></div>
        `;

        const btnTts = panel.querySelector('.sum-tts-btn');
        btnTts.addEventListener('click', () => {
            playAudio(summary, btnTts, `sum-${id}`);
        });

        const btnTrans = panel.querySelector('.sum-trans-btn');
        const transDiv = panel.querySelector('.summary-trans-text');
        btnTrans.addEventListener('click', async () => {
            if (!transDiv.classList.contains('hidden')) {
                transDiv.classList.add('hidden');
                btnTrans.classList.remove('active');
                return;
            }
            
            btnTrans.classList.add('active');
            transDiv.classList.remove('hidden');

            if (transDiv.innerHTML.trim() === '') {
                transDiv.innerHTML = `<i class="fa-solid fa-spinner fa-spin"></i> 요약본 번역 중...`;
                try {
                    const res = await fetch('/api/translate', {
                        method: 'POST',
                        headers: { 'Content-Type': 'application/json' },
                        body: JSON.stringify({ text: summary })
                    });
                    const data = await res.json();
                    if (data.status === 'success') {
                        transDiv.innerHTML = `<strong>[번역]</strong><br>${escapeHtml(data.translation)}`;
                    } else {
                        transDiv.innerHTML = `<span style="color:var(--danger)">번역 실패: ${data.message}</span>`;
                    }
                } catch (e) {
                    transDiv.innerHTML = `<span style="color:var(--danger)">네트워크 오류</span>`;
                }
            }
        });
    }

    // ==========================================
    // URL Health Check
    // ==========================================
    async function checkUrl(targetUrl) {
        try {
            const res = await fetch(`/api/check_url?url=${encodeURIComponent(targetUrl)}`);
            return await res.json();
        } catch (err) {
            return {
                url: targetUrl,
                status_code: 0,
                latency_ms: 0,
                status: 'error',
                message: `요청 실패: ${err.message}`
            };
        }
    }

    // Quick Bar Check
    btnCheckInputUrl.addEventListener('click', async () => {
        const url = customUrlInput.value.trim();
        if (!url) return;

        urlQuickResult.className = 'url-quick-result';
        urlQuickResult.innerHTML = '<i class="fa-solid fa-spinner fa-spin"></i> URL 연결 및 크롤링 가능 여부 확인 중...';
        urlQuickResult.classList.remove('hidden');

        const result = await checkUrl(url);

        urlQuickResult.className = `url-quick-result ${result.status}`;
        urlQuickResult.innerHTML = `
            <strong>[${result.status_code || '연결실패'}]</strong> ${escapeHtml(result.message)} 
            (응답속도: <strong>${result.latency_ms}ms</strong>, 탐지기사: <strong>${result.headlines_found}개</strong>)
        `;
    });

    btnLoadCustomUrl.addEventListener('click', () => {
        const url = customUrlInput.value.trim();
        if (!url) return;
        state.currentUrl = url;
        currentCategoryTitle.textContent = `📌 ${url} 크롤링 결과`;
        loadNews('custom', url, true);
    });

    // Modal Check
    btnUrlModal.addEventListener('click', () => {
        urlModal.classList.add('open');
    });

    function closeModal() {
        urlModal.classList.remove('open');
    }
    btnCloseModal.addEventListener('click', closeModal);
    btnCloseModalBottom.addEventListener('click', closeModal);
    urlModal.addEventListener('click', (e) => {
        if (e.target === urlModal) closeModal();
    });

    presetBtns.forEach(btn => {
        btn.addEventListener('click', () => {
            checkModalUrl.value = btn.getAttribute('data-url');
        });
    });

    btnRunModalCheck.addEventListener('click', async () => {
        const url = checkModalUrl.value.trim();
        if (!url) return;

        btnRunModalCheck.disabled = true;
        btnRunModalCheck.innerHTML = '<i class="fa-solid fa-spinner fa-spin"></i> 검사 중...';

        const result = await checkUrl(url);

        modalCheckResult.classList.remove('hidden');
        document.getElementById('resStatus').innerHTML = `<span class="badge ${result.status}">${result.status_code || '0'} (${result.status})</span>`;
        document.getElementById('resLatency').textContent = `${result.latency_ms} ms`;
        document.getElementById('resMethod').textContent = result.method || 'curl_cffi';
        document.getElementById('resHeadlines').textContent = `${result.headlines_found} 개 기사 식별`;
        
        const resMsg = document.getElementById('resMessage');
        resMsg.textContent = result.message;
        resMsg.className = `result-msg ${result.status}`;

        btnRunModalCheck.disabled = false;
        btnRunModalCheck.innerHTML = '<i class="fa-solid fa-play"></i> 검사 실행';
    });

    btnApplyModalUrl.addEventListener('click', () => {
        const url = checkModalUrl.value.trim();
        if (url) {
            customUrlInput.value = url;
            closeModal();
            state.currentUrl = url;
            currentCategoryTitle.textContent = `📌 ${url} 크롤링 결과`;
            loadNews('custom', url, true);
        }
    });

    // ==========================================
    // Category Tabs & Refresh
    // ==========================================
    catPills.forEach(pill => {
        pill.addEventListener('click', () => {
            catPills.forEach(p => p.classList.remove('active'));
            pill.classList.add('active');

            const cat = pill.getAttribute('data-cat');
            state.currentCategory = cat;
            state.currentUrl = '';
            customUrlInput.value = `https://apnews.com/${cat === 'top' ? '' : cat + '-news'}`;

            const titles = {
                'top': '📌 종합 헤드라인 (Top Stories)',
                'world': '📌 세계 뉴스 (World News)',
                'us': '📌 미국 뉴스 (US News)',
                'business': '📌 경제 및 금융 (Business)',
                'technology': '📌 테크 및 AI (Technology)',
                'sports': '📌 스포츠 (Sports)',
                'entertainment': '📌 연예 및 문화 (Entertainment)'
            };
            currentCategoryTitle.textContent = titles[cat] || '📌 AP 기사 헤드라인';
            loadNews(cat, '', false);
        });
    });

    btnRefresh.addEventListener('click', () => {
        loadNews(state.currentCategory, state.currentUrl, true);
    });

    // ==========================================
    // System Status & Helper
    // ==========================================
    async function updateStats() {
        try {
            const res = await fetch('/api/status');
            const data = await res.json();
            if (data.status === 'healthy') {
                statArticles.textContent = data.cached_articles;
                statTrans.textContent = data.cached_translations;
                statAnalyses.textContent = data.cached_analyses;
                if (statSummaries) statSummaries.textContent = data.cached_summaries || 0;
            }
        } catch (e) {
            console.warn('Status fetch error:', e);
        }
    }

    function updateConnectionStatus(type, msg) {
        connectionBadge.className = `connection-status ${type}`;
        connectionBadge.querySelector('.status-text').textContent = msg || '연결 완료';
    }

    function escapeHtml(text) {
        if (!text) return '';
        const map = {
            '&': '&amp;',
            '<': '&lt;',
            '>': '&gt;',
            '"': '&quot;',
            "'": '&#039;'
        };
        return text.toString().replace(/[&<>"']/g, m => map[m]);
    }

    // Initialize initial load
    loadNews('top', '', false);
    // Initial status check
    updateStats();
});
