/**
 * 360° 全景导览公共逻辑
 * 用法: initViewer({ scenes, sceneOrder, loadTimeout })
 */

const ARROW_RIGHT = '<svg viewBox="0 0 24 24" fill="none" stroke="#333" stroke-width="2"><path d="M5 12h14M12 5l7 7-7 7"/></svg>';
const ARROW_LEFT  = '<svg viewBox="0 0 24 24" fill="none" stroke="#333" stroke-width="2"><path d="M19 12H5M12 5l-7 7 7 7"/></svg>';

function makeHotspots(sceneId, order) {
    const idx = order.indexOf(sceneId);
    const prev = order[(idx - 1 + order.length) % order.length];
    const next = order[(idx + 1) % order.length];
    return [
        {
            pitch: 0, yaw: 90,
            type: 'custom', cssClass: 'custom-hotspot',
            createTooltipFunc: (el) => { el.innerHTML = ARROW_RIGHT; el.title = '前往 ' + next; },
            clickHandlerFunc: () => switchScene(next)
        },
        {
            pitch: 0, yaw: -90,
            type: 'custom', cssClass: 'custom-hotspot',
            createTooltipFunc: (el) => { el.innerHTML = ARROW_LEFT; el.title = '返回 ' + prev; },
            clickHandlerFunc: () => switchScene(prev)
        }
    ];
}

let viewer;

function switchScene(sceneId) {
    viewer.loadScene(sceneId);
    document.querySelectorAll('.scene-btn').forEach(btn => {
        btn.classList.toggle('active', btn.dataset.scene === sceneId);
    });
}

function initViewer(config) {
    const { scenes, sceneOrder, loadTimeout } = config;

    // 注入热点到每个场景
    for (const id of sceneOrder) {
        scenes[id].hotSpots = makeHotspots(id, sceneOrder);
    }

    viewer = pannellum.viewer('panorama', {
        default: {
            hfov: 110,
            minHfov: 50,
            maxHfov: 120,
            autoLoad: true,
            compass: false,
            pitch: 5,
        },
        firstScene: sceneOrder[0],
        scenes
    });

    // loading 隐藏
    function hideLoading() {
        document.getElementById('loadingOverlay').classList.add('hidden');
    }
    viewer.on('load', hideLoading);
    setTimeout(hideLoading, loadTimeout);

    // 导航按钮
    document.querySelectorAll('.scene-btn').forEach(btn => {
        btn.addEventListener('click', () => switchScene(btn.dataset.scene));
    });

    // 自动旋转
    let autoRotate = true;
    const rotateBtn = document.getElementById('autoRotateBtn');
    rotateBtn.classList.add('active');
    rotateBtn.addEventListener('click', () => {
        autoRotate = !autoRotate;
        rotateBtn.classList.toggle('active', autoRotate);
        viewer.setAutoRotate(autoRotate ? -2 : 0);
    });

    // 提示文字淡出
    document.getElementById('panorama').addEventListener('mousedown', () => {
        document.getElementById('hint').style.opacity = '0';
    }, { once: true });
}
