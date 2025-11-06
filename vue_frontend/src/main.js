// 应用入口：挂载 Vue 应用、注册 Element Plus、挂载路由
import { createApp } from 'vue';
import ElementPlus from 'element-plus';
import 'element-plus/dist/index.css';
import '@/assets/styles/auth-common.css';
import App from './App.vue';
import router from './router';

// 开发模式下，尽早注册全局处理，抑制特定 ResizeObserver 循环告警导致的 dev overlay 红屏
const __isDev = (typeof process !== 'undefined' && process.env && process.env.NODE_ENV === 'development');
if (__isDev) {
	const isResizeObserverMsg = (msg) => typeof msg === 'string' && msg.includes('ResizeObserver');
	// 观察 dev overlay DOM，如仅包含 ResizeObserver 文本则隐藏之（不影响其它真实错误）
	const hideResizeOverlay = () => {
		try {
			const overlay = document.querySelector('#webpack-dev-server-client-overlay')
				|| document.querySelector('iframe#webpack-dev-server-client-overlay');
			if (!overlay) return;
			// overlay 可能是 iframe，尝试取文本
			let text = '';
			try {
				if (overlay.tagName === 'IFRAME' && overlay.contentDocument) {
					text = overlay.contentDocument.body?.innerText || '';
				} else {
					text = overlay.innerText || '';
				}
			} catch (_) {}
			if (text && isResizeObserverMsg(text)) {
				// 直接隐藏 overlay
				overlay.style.display = 'none';
				overlay.setAttribute('aria-hidden', 'true');
			}
		} catch (_) {}
	};
	const mo = new MutationObserver(() => hideResizeOverlay());
	mo.observe(document.documentElement, { childList: true, subtree: true });
	// 初始触发一次
	if (document.readyState === 'complete' || document.readyState === 'interactive') {
		setTimeout(hideResizeOverlay, 0);
	} else {
		window.addEventListener('DOMContentLoaded', hideResizeOverlay, { once: true });
	}
	// 捕获阶段优先处理
	window.addEventListener(
		'error',
		(e) => {
			const msg = (e && (e.message || (e.error && e.error.message))) || '';
			if (isResizeObserverMsg(String(msg))) {
				e.stopImmediatePropagation();
				e.preventDefault();
			}
		},
		true
	);
	window.addEventListener(
		'unhandledrejection',
		(e) => {
			const reason = e && e.reason ? String(e.reason) : '';
			if (isResizeObserverMsg(reason)) {
				e.preventDefault();
				e.stopImmediatePropagation();
			}
		},
		true
	);
	// 冒泡阶段兜底
	window.addEventListener('error', (e) => {
		const msg = (e && (e.message || (e.error && e.error.message))) || '';
		if (isResizeObserverMsg(String(msg))) {
			e.stopImmediatePropagation();
		}
	});
	window.addEventListener('unhandledrejection', (e) => {
		const reason = e && e.reason ? String(e.reason) : '';
		if (isResizeObserverMsg(reason)) {
			e.preventDefault();
		}
	});
}

const app = createApp(App);
app.use(ElementPlus);
app.use(router);
app.mount('#app');

// （保留）挂载后逻辑无需再重复设监听
