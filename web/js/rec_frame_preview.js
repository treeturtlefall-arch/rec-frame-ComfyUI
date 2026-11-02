/**
 * rec-frame-ComfyUI: リアルタイム追従プレビュー機能拡張
 *
 * `RecFrameOverlay` のウィジェット変更を検知し、直下に接続された
 * `Preview REC Overlay` (`RecFramePreview`) ノードへ即座に描画画像を反映する。
 */
import { app } from "../../../scripts/app.js";

const OVERLAY_NODE_TYPES = new Set([
    "RecFrameImageOverlay",
    "RecFrameVideoOverlay",
    "RecFrameOverlay",
    "RecFrameCustomOverlay",
]);

// スライダー連続ドラッグ等の負荷軽減デバウンス
function debounce(fn, waitMs = 60) {
    let timer = null;
    return function (...args) {
        if (timer) clearTimeout(timer);
        timer = setTimeout(() => {
            timer = null;
            fn.apply(this, args);
        }, waitMs);
    };
}

/**
 * RecFrameOverlay ノードから現在の全ウィジェット値を key-value 辞書として抽出する。
 */
function extractWidgetParams(node) {
    const params = {};
    if (!node || !node.widgets) return params;
    for (const w of node.widgets) {
        if (w.name) {
            params[w.name] = w.value;
        }
    }
    return params;
}

/**
 * 指定した RecFramePreview ノードに接続されている RecFrameOverlay ノードを探索する。
 */
function findConnectedOverlayNode(previewNode) {
    if (!previewNode || !previewNode.inputs || !app.graph || !app.graph.links) return null;
    const input = previewNode.inputs.find((i) => i.name === "overlay_rgba");
    if (!input || input.link == null) return null;

    const linkInfo = app.graph.links[input.link] || (app.graph.links.get && app.graph.links.get(input.link));
    if (!linkInfo) return null;

    const originNode = app.graph.getNodeById(linkInfo.origin_id);
    if (!originNode) return null;

    const type = originNode.type || originNode.comfyClass;
    if (OVERLAY_NODE_TYPES.has(type)) {
        return originNode;
    }
    return null;
}

/**
 * 指定した RecFrameOverlay ノードから接続されている全 RecFramePreview ノードを探索する。
 */
function findConnectedPreviewNodes(overlayNode) {
    const previews = [];
    if (!overlayNode || !overlayNode.outputs || !app.graph || !app.graph.links) return previews;

    // overlay_rgba は通常 index 1
    for (let outIdx = 0; outIdx < overlayNode.outputs.length; outIdx++) {
        const out = overlayNode.outputs[outIdx];
        if (out && out.links && out.links.length > 0) {
            for (const linkId of out.links) {
                const linkInfo = app.graph.links[linkId] || (app.graph.links.get && app.graph.links.get(linkId));
                if (!linkInfo) continue;
                const targetNode = app.graph.getNodeById(linkInfo.target_id);
                if (targetNode) {
                    const targetType = targetNode.type || targetNode.comfyClass;
                    if (targetType === "RecFramePreview") {
                        if (!previews.includes(targetNode)) {
                            previews.push(targetNode);
                        }
                    }
                }
            }
        }
    }
    return previews;
}

/**
 * プレビュー API を呼び出して RecFramePreview ノードの描画画像を更新する。
 */
async function updatePreviewNodeImage(previewNode, overlayNode = null) {
    if (!previewNode) return;
    const origin = overlayNode || findConnectedOverlayNode(previewNode);
    if (!origin) return;

    // パラメータ収集
    const params = extractWidgetParams(origin);

    // プレビュー自身のパラメータ (bg_color, preview_size) を付与
    if (previewNode.widgets) {
        for (const w of previewNode.widgets) {
            if (w.name) {
                params[w.name] = w.value;
            }
        }
    }

    try {
        const response = await fetch("/rec_frame/preview", {
            method: "POST",
            headers: {
                "Content-Type": "application/json",
            },
            body: JSON.stringify(params),
        });

        if (!response.ok) return;

        const blob = await response.blob();
        const objectUrl = URL.createObjectURL(blob);
        const img = new Image();
        img.onload = () => {
            if (previewNode._recPrevObjectUrl) {
                URL.revokeObjectURL(previewNode._recPrevObjectUrl);
            }
            previewNode._recPrevObjectUrl = objectUrl;
            previewNode.imgs = [img];
            if (previewNode.setSizeForImage) {
                previewNode.setSizeForImage();
            } else if (!previewNode.size || previewNode.size[1] < 200) {
                // デフォルトサイズ確保
                previewNode.size = [Math.max(previewNode.size?.[0] || 240, 280), Math.max(previewNode.size?.[1] || 200, 240)];
            }
            if (app.graph) {
                app.graph.setDirtyCanvas(true, true);
            }
        };
        img.onerror = () => {
            URL.revokeObjectURL(objectUrl);
        };
        img.src = objectUrl;
    } catch (err) {
        // バックエンド非同期中や一時的エラーは無視
    }
}

const debouncedUpdatePreview = debounce((previewNode, overlayNode) => {
    updatePreviewNodeImage(previewNode, overlayNode);
}, 60);

app.registerExtension({
    name: "rec_frame.realtime_preview",

    async beforeRegisterNodeDef(nodeType, nodeData) {
        const typeName = nodeData.name;

        // 1. 各種 RecFrame オーバーレイノード側のフック
        if (OVERLAY_NODE_TYPES.has(typeName)) {
            const onNodeCreated = nodeType.prototype.onNodeCreated;
            nodeType.prototype.onNodeCreated = function () {
                const r = onNodeCreated ? onNodeCreated.apply(this, arguments) : undefined;

                const notifyConnectedPreviews = () => {
                    const previews = findConnectedPreviewNodes(this);
                    for (const prev of previews) {
                        debouncedUpdatePreview(prev, this);
                    }
                };

                // 各ウィジェットの変更イベントにフック
                if (this.widgets) {
                    for (const w of this.widgets) {
                        const origCallback = w.callback;
                        w.callback = function () {
                            if (origCallback) origCallback.apply(this, arguments);
                            notifyConnectedPreviews();
                        };
                    }
                }

                // リンク接続・切断時の検知
                const origConnectionsChange = this.onConnectionsChange;
                this.onConnectionsChange = function (type, index, isConnected, linkInfo) {
                    if (origConnectionsChange) origConnectionsChange.apply(this, arguments);
                    if (isConnected) {
                        setTimeout(notifyConnectedPreviews, 50);
                    }
                };

                return r;
            };
        }

        // 2. RecFramePreview ノード側のフック
        if (typeName === "RecFramePreview") {
            const onNodeCreated = nodeType.prototype.onNodeCreated;
            nodeType.prototype.onNodeCreated = function () {
                const r = onNodeCreated ? onNodeCreated.apply(this, arguments) : undefined;

                const triggerUpdate = () => {
                    const origin = findConnectedOverlayNode(this);
                    if (origin) {
                        debouncedUpdatePreview(this, origin);
                    }
                };

                // 自身のウィジェット変更 (bg_color, preview_size) にフック
                if (this.widgets) {
                    for (const w of this.widgets) {
                        const origCallback = w.callback;
                        w.callback = function () {
                            if (origCallback) origCallback.apply(this, arguments);
                            triggerUpdate();
                        };
                    }
                }

                // リンク接続時の検知
                const origConnectionsChange = this.onConnectionsChange;
                this.onConnectionsChange = function (type, index, isConnected, linkInfo) {
                    if (origConnectionsChange) origConnectionsChange.apply(this, arguments);
                    if (isConnected) {
                        setTimeout(triggerUpdate, 50);
                    }
                };

                // ワークフロー読み込みによるウィジェット復元時のプレビュー更新
                const origOnConfigure = this.onConfigure;
                this.onConfigure = function () {
                    if (origOnConfigure) origOnConfigure.apply(this, arguments);
                    setTimeout(triggerUpdate, 150);
                };

                // 初期プレビュー描画の試行
                setTimeout(triggerUpdate, 200);

                return r;
            };
        }
    },
});
