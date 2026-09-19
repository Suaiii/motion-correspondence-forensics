# AL64：OpenVid-HD来源与时间字段公开协议审查

planagent，独立于AL36。AL63确认AIGVDBench以OpenVid-HD作为prompt和真实视频来源，但论文正文没有给样本级原生PTS、祖先图或输入哈希。本包只核对OpenVid-HD的公开primary数据说明、论文或作者README，不访问样本、manifest、媒体、下载链接、权重或最终集。

先用至多2个公开primary入口确定OpenVid-HD身份、版本和作者；只读一个主要版本的来源、视频时间字段、压缩/帧率、许可和数据构成段落。若页面需要登录、验证码或下载权限，记录缺口并停止，不换身份绕过。

核对问题：数据是否公开定义了原始视频来源和时间字段（PTS/time_base或仅容器/标称FPS）、是否提供祖先/去重/处理链、AIGVDBench引用的OpenVid-HD版本是否能与论文对应、真实视频是否可作为同prompt配对的视觉祖先。只作协议边界审查；不把作者总体数量或论文性能作为本项目数据验收。

交付 reviews/AL64_OPENVIDHD_PROVENANCE_REVIEW_20260919.md 与 AL64_SOURCE_RECORD_20260919.json，记录版本、URL、阅读范围、字节或内容SHA256和unknown项。无论结果通过或缺口，都不释放RS02/RS03、最终集或服务器/GPU。AL36保持独立未派发。
