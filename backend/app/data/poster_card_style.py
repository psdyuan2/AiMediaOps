
TEMPLATES = {
    # ---------------------------------------------------------
    # 风格一：杂志排版风 (Editorial)
    # 特点：衬线字体，优雅的留白，大标题，适合阅读
    # ---------------------------------------------------------
    "editorial": """
    <!DOCTYPE html>
    <html lang="zh-CN">
    <head>
        <meta charset="UTF-8">
        <style>
            @import url('https://fonts.googleapis.com/css2?family=Noto+Serif+SC:wght@400;700;900&display=swap');

            body { margin: 0; padding: 0; background: #fdfbf7; font-family: 'Noto Serif SC', 'Songti SC', serif; }
            .poster-container {
                width: 400px;
                height: 700px;
                background: #fdfbf7;
                padding: 40px;
                box-sizing: border-box;
                display: flex;
                flex-direction: column;
                position: relative;
                color: #2c2c2c;
                border: 12px solid #2c2c2c; /* 粗边框 */
            }
            .header {
                margin-bottom: 30px;
                border-bottom: 2px solid #2c2c2c;
                padding-bottom: 20px;
            }
            .title {
                font-size: 42px;
                font-weight: 900;
                line-height: 1.1;
                margin: 0 0 10px 0;
            }
            .subtitle {
                font-size: 16px;
                font-weight: 400;
                font-style: italic;
                color: #666;
                margin: 0;
            }
            .content {
                flex-grow: 1;
                font-size: 17px;
                line-height: 1.8;
                text-align: justify;
                white-space: pre-wrap; /* 保留换行符 */
            }
            .note-box {
                margin-top: 30px;
                background: #2c2c2c;
                color: #fdfbf7;
                padding: 15px;
                font-size: 12px;
                text-align: center;
                font-weight: bold;
                letter-spacing: 2px;
                text-transform: uppercase;
            }
            /* 装饰性引号 */
            .quote-mark {
                position: absolute;
                font-size: 120px;
                color: rgba(0,0,0,0.05);
                font-family: serif;
                top: 140px;
                left: 20px;
                z-index: 0;
                pointer-events: none;
            }
        </style>
    </head>
    <body>
        <div id="poster" class="poster-container">
            <div class="quote-mark">“</div>
            <div class="header" style="z-index:1;">
                <h1 class="title">{{ title }}</h1>
                <p class="subtitle">{{ subtitle }}</p>
            </div>
            <div class="content" style="z-index:1;">
                {{ content }}
            </div>
            <div class="note-box">
                {{ note }}
            </div>
        </div>
    </body>
    </html>
    """,

    # ---------------------------------------------------------
    # 风格二：科技卡片风 (TechCard)
    # 特点：深色背景，磨砂玻璃感，代码字体，适合技术内容
    # ---------------------------------------------------------
    "tech": """
    <!DOCTYPE html>
    <html lang="zh-CN">
    <head>
        <meta charset="UTF-8">
        <style>
            body { margin: 0; padding: 0; background: #000; font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif; }
            .poster-container {
                width: 400px;
                height: 700px;
                background: linear-gradient(135deg, #1e2024 0%, #171717 100%);
                padding: 30px;
                box-sizing: border-box;
                display: flex;
                flex-direction: column;
                color: #fff;
                position: relative;
            }
            /* 顶部装饰条 */
            .status-bar {
                display: flex;
                gap: 6px;
                margin-bottom: 25px;
            }
            .dot { width: 12px; height: 12px; border-radius: 50%; }
            .red { background: #ff5f56; }
            .yellow { background: #ffbd2e; }
            .green { background: #27c93f; }

            .card {
                background: rgba(255, 255, 255, 0.05);
                border: 1px solid rgba(255, 255, 255, 0.1);
                border-radius: 16px;
                padding: 25px;
                flex-grow: 1;
                display: flex;
                flex-direction: column;
                backdrop-filter: blur(10px);
                box-shadow: 0 20px 50px rgba(0,0,0,0.5);
            }
            .subtitle {
                color: #5bbaff;
                font-size: 13px;
                font-weight: 700;
                text-transform: uppercase;
                letter-spacing: 1px;
                margin-bottom: 10px;
            }
            .title {
                font-size: 34px;
                font-weight: 800;
                line-height: 1.2;
                margin: 0 0 20px 0;
                background: linear-gradient(90deg, #fff, #aaa);
                -webkit-background-clip: text;
                -webkit-text-fill-color: transparent;
            }
            .divider {
                height: 1px;
                background: rgba(255,255,255,0.1);
                margin-bottom: 20px;
            }
            .content {
                font-size: 15px;
                line-height: 1.7;
                color: #d1d5db;
                font-family: 'Menlo', 'Monaco', monospace; /* 代码风格字体 */
                white-space: pre-wrap;
            }
            .note {
                margin-top: auto;
                padding-top: 20px;
                font-size: 12px;
                color: #6b7280;
                display: flex;
                align-items: center;
                gap: 8px;
            }
            .note::before {
                content: '';
                display: block;
                width: 8px;
                height: 8px;
                background: #27c93f;
                border-radius: 50%;
                box-shadow: 0 0 10px #27c93f;
            }
        </style>
    </head>
    <body>
        <div id="poster" class="poster-container">
            <div class="status-bar">
                <div class="dot red"></div>
                <div class="dot yellow"></div>
                <div class="dot green"></div>
            </div>
            <div class="card">
                <div class="subtitle">{{ subtitle }}</div>
                <h1 class="title">{{ title }}</h1>
                <div class="divider"></div>
                <div class="content">{{ content }}</div>
                <div class="note">
                    {{ note }}
                </div>
            </div>
        </div>
    </body>
    </html>
    """,

    # ---------------------------------------------------------
    # 风格三：新中式/道家风 (ZenTea)
    # 特点：低饱和度绿色，宋体，边框，古朴，适合你的道家项目
    # ---------------------------------------------------------
    "zen": """
    <!DOCTYPE html>
    <html lang="zh-CN">
    <head>
        <meta charset="UTF-8">
        <style>
            @import url('https://fonts.googleapis.com/css2?family=Noto+Serif+SC:wght@300;600&display=swap');

            body { margin: 0; padding: 0; background: #e0e5df; font-family: 'Noto Serif SC', serif; }
            .poster-container {
                width: 400px;
                height: 700px;
                background: #e9ece8; /* 浅豆沙绿 */
                padding: 25px;
                box-sizing: border-box;
                display: flex;
                flex-direction: column;
                position: relative;
                color: #3d4c43; /* 深墨绿 */
            }
            /* 内边框 */
            .inner-border {
                border: 1px solid #3d4c43;
                height: 100%;
                padding: 30px;
                box-sizing: border-box;
                display: flex;
                flex-direction: column;
                align-items: center;
                position: relative;
            }
            /* 四角的装饰 */
            .corner {
                position: absolute;
                width: 10px;
                height: 10px;
                border: 3px solid #3d4c43;
                transition: all 0.3s;
            }
            .tl { top: -2px; left: -2px; border-right: none; border-bottom: none; }
            .tr { top: -2px; right: -2px; border-left: none; border-bottom: none; }
            .bl { bottom: -2px; left: -2px; border-right: none; border-top: none; }
            .br { bottom: -2px; right: -2px; border-left: none; border-top: none; }

            .subtitle-box {
                background: #3d4c43;
                color: #e9ece8;
                padding: 4px 12px;
                font-size: 14px;
                margin-bottom: 20px;
                border-radius: 20px;
            }
            .title {
                font-size: 36px;
                font-weight: 600;
                margin: 0 0 40px 0;
                letter-spacing: 4px;
                text-align: center;
                border-bottom: 1px solid rgba(61, 76, 67, 0.3);
                padding-bottom: 20px;
                width: 100%;
            }
            .content {
                font-size: 18px;
                line-height: 2;
                text-align: left; /* 也可以尝试 justify */
                flex-grow: 1;
                width: 100%;
                white-space: pre-wrap;
            }
            .stamp-area {
                margin-top: 20px;
                width: 100%;
                display: flex;
                justify-content: flex-end;
                align-items: center;
                gap: 10px;
            }
            .note {
                font-size: 14px;
                color: #66706a;
                writing-mode: vertical-rl; /* 竖排文字 */
                letter-spacing: 2px;
            }
            .seal {
                width: 40px;
                height: 40px;
                border: 2px solid #b24638; /* 印章红 */
                color: #b24638;
                font-size: 20px;
                display: flex;
                align-items: center;
                justify-content: center;
                border-radius: 4px;
                font-weight: bold;
                opacity: 0.8;
            }
        </style>
    </head>
    <body>
        <div id="poster" class="poster-container">
            <div class="inner-border">
                <div class="corner tl"></div>
                <div class="corner tr"></div>
                <div class="corner bl"></div>
                <div class="corner br"></div>

                <div class="subtitle-box">{{ subtitle }}</div>
                <h1 class="title">{{ title }}</h1>
                <div class="content">{{ content }}</div>

                <div class="stamp-area">
                    <div class="note">{{ note }}</div>
                    <div class="seal">道</div>
                </div>
            </div>
        </div>
    </body>
    </html>
    """,
    "pop": """
    <!DOCTYPE html>
    <html lang="zh-CN">
    <head>
        <meta charset="UTF-8">
        <style>
            body { margin: 0; padding: 0; background: #FFD028; font-family: 'Arial Black', 'Helvetica Neue', sans-serif; }
            .poster-container {
                width: 400px;
                height: 700px;
                background: #FFD028; /* 亮黄背景 */
                padding: 30px;
                box-sizing: border-box;
                display: flex;
                flex-direction: column;
                position: relative;
                color: #000;
            }
            .card {
                background: #fff;
                border: 4px solid #000;
                box-shadow: 8px 8px 0px #000; /* 硬阴影 */
                padding: 25px;
                flex-grow: 1;
                display: flex;
                flex-direction: column;
                position: relative;
            }
            .subtitle-badge {
                background: #FF6B6B; /* 珊瑚红 */
                color: #fff;
                border: 2px solid #000;
                padding: 5px 15px;
                font-weight: bold;
                font-size: 14px;
                display: inline-block;
                transform: rotate(-2deg);
                margin-bottom: 15px;
                align-self: flex-start;
                box-shadow: 3px 3px 0px #000;
            }
            .title {
                font-size: 38px;
                font-weight: 900;
                line-height: 1.1;
                margin: 0 0 20px 0;
                text-transform: uppercase;
                background: #54A0FF; /* 蓝色高亮条 */
                display: inline;
                box-decoration-break: clone;
                padding: 2px 5px;
            }
            .content {
                font-size: 16px;
                font-weight: 600;
                line-height: 1.6;
                margin-top: 20px;
                white-space: pre-wrap;
                flex-grow: 1;
            }
            .note-area {
                margin-top: 20px;
                border-top: 4px solid #000;
                padding-top: 15px;
                font-weight: 800;
                font-size: 14px;
                display: flex;
                justify-content: space-between;
                align-items: center;
            }
            .icon {
                font-size: 24px;
            }
        </style>
    </head>
    <body>
        <div id="poster" class="poster-container">
            <div class="card">
                <div class="subtitle-badge">{{ subtitle }}</div>
                <div><span class="title">{{ title }}</span></div>

                <div class="content">{{ content }}</div>

                <div class="note-area">
                    <span>{{ note }}</span>
                    <span class="icon">★</span>
                </div>
            </div>
        </div>
    </body>
    </html>
    """,

    # ---------------------------------------------------------
    # 风格五：治愈系/INS风 (Soft Healing)
    # 特点：圆角、奶油色调、柔和阴影、可爱字体。适合情感文案、生活记录、好物分享。
    # ---------------------------------------------------------
    "healing": """
    <!DOCTYPE html>
    <html lang="zh-CN">
    <head>
        <meta charset="UTF-8">
        <style>
            /* 尝试加载圆体，如果没有则退化为系统字体 */
            @import url('https://fonts.googleapis.com/css2?family=Varela+Round&display=swap');

            body { margin: 0; padding: 0; background: #FDF6F0; font-family: 'Varela Round', 'Yuanti SC', 'Microsoft YaHei', sans-serif; }
            .poster-container {
                width: 400px;
                height: 700px;
                background: #FDF6F0; /* 奶油米色 */
                padding: 40px;
                box-sizing: border-box;
                display: flex;
                flex-direction: column;
                align-items: center;
            }
            .card {
                background: #FFF;
                width: 100%;
                height: 100%;
                border-radius: 24px;
                padding: 35px;
                box-sizing: border-box;
                box-shadow: 0 10px 30px rgba(229, 194, 176, 0.4); /* 柔和的暖色阴影 */
                display: flex;
                flex-direction: column;
            }
            .subtitle {
                color: #BCAAA4;
                font-size: 14px;
                letter-spacing: 2px;
                text-align: center;
                margin-bottom: 10px;
            }
            .title {
                font-size: 32px;
                color: #5D4037; /* 深咖啡色 */
                text-align: center;
                margin: 0 0 30px 0;
                font-weight: 600;
            }
            .content-box {
                background: #FAFAFA;
                border-radius: 16px;
                padding: 20px;
                flex-grow: 1;
                margin-bottom: 20px;
            }
            .content {
                font-size: 16px;
                color: #795548;
                line-height: 1.8;
                white-space: pre-wrap;
            }
            .note {
                text-align: center;
                font-size: 12px;
                color: #D7CCC8;
                border-top: 1px dashed #E0E0E0;
                padding-top: 15px;
            }
            /* 装饰圆点 */
            .deco-dot {
                width: 8px;
                height: 8px;
                background: #FFCCBC;
                border-radius: 50%;
                margin: 0 auto 15px auto;
            }
        </style>
    </head>
    <body>
        <div id="poster" class="poster-container">
            <div class="card">
                <div class="subtitle">{{ subtitle }}</div>
                <h1 class="title">{{ title }}</h1>
                <div class="deco-dot"></div>

                <div class="content-box">
                    <div class="content">{{ content }}</div>
                </div>

                <div class="note">
                    ✿ {{ note }} ✿
                </div>
            </div>
        </div>
    </body>
    </html>
    """,

    # ---------------------------------------------------------
    # 风格六：Notion笔记风 (Knowledge)
    # 特点：极简、结构化、Emoji图标、灰色背景块。适合干货教程、知识点总结。
    # ---------------------------------------------------------
    "notion": """
    <!DOCTYPE html>
    <html lang="zh-CN">
    <head>
        <meta charset="UTF-8">
        <style>
            body { margin: 0; padding: 0; background: #FFFFFF; font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Helvetica, Arial, sans-serif; }
            .poster-container {
                width: 400px;
                height: 700px;
                background: #FFFFFF;
                padding: 40px;
                box-sizing: border-box;
                display: flex;
                flex-direction: column;
                color: #37352F;
            }
            .icon {
                font-size: 48px;
                margin-bottom: 20px;
            }
            .title {
                font-size: 36px;
                font-weight: 700;
                line-height: 1.2;
                margin: 0 0 10px 0;
            }
            .subtitle-tag {
                display: inline-block;
                background: #E8DEEE; /* 淡紫色背景 */
                color: #4A2B60;
                padding: 4px 8px;
                border-radius: 4px;
                font-size: 14px;
                margin-bottom: 30px;
            }
            .callout {
                background: #F1F1EF; /* Notion 经典灰 */
                padding: 20px;
                border-radius: 5px;
                display: flex;
                flex-direction: column;
                flex-grow: 1;
            }
            .content {
                font-size: 16px;
                line-height: 1.7;
                white-space: pre-wrap;
            }
            .divider {
                border-bottom: 1px solid #E9E9E8;
                margin: 20px 0;
            }
            .note {
                font-size: 12px;
                color: #9B9A97;
                display: flex;
                align-items: center;
                gap: 5px;
            }
            .note::before {
                content: '●';
                font-size: 6px;
            }
        </style>
    </head>
    <body>
        <div id="poster" class="poster-container">
            <div class="icon">📑</div>
            <h1 class="title">{{ title }}</h1>
            <div><span class="subtitle-tag">{{ subtitle }}</span></div>

            <div class="callout">
                <div class="content">{{ content }}</div>
                <div class="divider"></div>
                <div class="note">{{ note }}</div>
            </div>
        </div>
    </body>
    </html>
    """,

    # ---------------------------------------------------------
    # 风格七：复古小票风 (Receipt)
    # 特点：单色、等宽字体、锯齿边缘、虚线。适合清单、记录、碎碎念。
    # ---------------------------------------------------------
    "receipt": """
    <!DOCTYPE html>
    <html lang="zh-CN">
    <head>
        <meta charset="UTF-8">
        <style>
            @import url('https://fonts.googleapis.com/css2?family=Courier+Prime&display=swap');

            body { margin: 0; padding: 0; background: #e0e0e0; font-family: 'Courier Prime', 'Courier New', Courier, monospace; }
            .poster-container {
                width: 400px;
                height: 700px;
                background: #e0e0e0;
                padding: 30px;
                box-sizing: border-box;
                display: flex;
                justify-content: center;
                align-items: flex-start;
            }
            .receipt {
                width: 100%;
                background: #fff;
                padding: 25px;
                box-shadow: 0 5px 15px rgba(0,0,0,0.1);
                position: relative;
                /* 锯齿效果利用CSS radial-gradient实现 */
                --mask: radial-gradient(circle at bottom, transparent 6px, black 6.5px) bottom / 100% 20px repeat-x;
                /* 简单的底部锯齿模拟，或者直接切平 */
                border-top: 1px solid #ccc;
            }
            /* 模拟底部锯齿 */
            .receipt::after {
                content: "";
                position: absolute;
                bottom: -10px;
                left: 0;
                width: 100%;
                height: 10px;
                background: linear-gradient(45deg, transparent 33.333%, #fff 33.333%, #fff 66.667%, transparent 66.667%), 
                            linear-gradient(-45deg, transparent 33.333%, #fff 33.333%, #fff 66.667%, transparent 66.667%);
                background-size: 20px 40px;
            }

            .header-center {
                text-align: center;
                margin-bottom: 20px;
            }
            .title {
                font-size: 24px;
                font-weight: bold;
                text-transform: uppercase;
                margin: 10px 0;
            }
            .subtitle {
                font-size: 12px;
                border-top: 1px dashed #000;
                border-bottom: 1px dashed #000;
                padding: 8px 0;
                margin: 10px 0;
            }
            .content {
                font-size: 14px;
                line-height: 1.6;
                white-space: pre-wrap;
                margin-bottom: 30px;
                text-align: left;
            }
            .barcode {
                height: 40px;
                background: repeating-linear-gradient(
                    to right,
                    #000,
                    #000 2px,
                    #fff 2px,
                    #fff 4px
                );
                margin: 20px 0;
                width: 80%;
                margin-left: 10%;
            }
            .note {
                text-align: center;
                font-size: 10px;
                margin-top: 10px;
            }
        </style>
    </head>
    <body>
        <div id="poster" class="poster-container">
            <div class="receipt">
                <div class="header-center">
                    <div>**************************</div>
                    <div class="title">{{ title }}</div>
                    <div>**************************</div>
                    <div class="subtitle">DATE: {{ subtitle }}</div>
                </div>

                <div class="content">
{{ content }}
                </div>

                <div class="barcode"></div>
                <div class="note">
                    {{ note }}<br>
                    THANK YOU FOR READING
                </div>
            </div>
        </div>
    </body>
    </html>
    """
}