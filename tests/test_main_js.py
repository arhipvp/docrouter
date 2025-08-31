import subprocess
import textwrap
from pathlib import Path


def test_main_js_rotate_crop(tmp_path):
    main_js = Path(__file__).resolve().parent.parent / "src" / "web_app" / "static" / "dist" / "main.js"
    js_code = textwrap.dedent(
        """
        const fs = require('fs');
        const path = require('path');
        const assert = require('assert');
        const { pathToFileURL } = require('url');

        class Element {
          constructor(tag = 'div') {
            this.tag = tag;
            this.children = [];
            this.style = {};
            this.dataset = {};
            this.events = {};
            this.classList = { add(){}, remove(){} };
            this.innerHTML = '';
            this.textContent = '';
            this.value = '';
            this.firstChild = null;
          }
          appendChild(child) { this.children.push(child); if (!this.firstChild) this.firstChild = child; return child; }
          insertBefore(node) { this.children.push(node); return node; }
          addEventListener(type, cb) { this.events[type] = cb; }
          dispatchEvent(evt) { (this.events[evt.type] || (()=>{}))(evt); }
          click() { this.dispatchEvent({ type: 'click', target: this }); }
          reset() { this.value = ''; }
          getContext() { return { clearRect(){}, drawImage(){} }; }
          querySelector() { return new Element(); }
          querySelectorAll() { return []; }
        }

        const elements = {};
        function getEl(id) {
          if (!elements[id]) elements[id] = new Element();
          return elements[id];
        }

        const document = {
          getElementById: getEl,
          querySelector: (sel) => {
            if (sel === 'form') return getEl('form');
            if (sel === '.container') return getEl('container');
            if (sel.startsWith('#')) return getEl(sel.slice(1));
            return null;
          },
          querySelectorAll: () => [],
          createElement: (tag) => new Element(tag),
          addEventListener: (type, cb) => { if (type === 'DOMContentLoaded') document._dom = cb; },
          dispatchEvent: (evt) => { if (evt.type === 'DOMContentLoaded') document._dom?.(evt); }
        };

        getEl('container').firstChild = new Element();
        getEl('container').firstChild.nextSibling = new Element();

        global.document = document;
        global.window = { document };
        global.navigator = {};
        global.fetch = () => Promise.resolve({ ok: false });
        global.alert = () => {};
        global.FormData = class { append(){} };

        class FakeFile {
          constructor(parts, name, opts){ this.parts = parts; this.name = name; this.type = opts?.type; }
        }
        global.File = FakeFile;
        global.Blob = class { constructor(parts, opts){ this.parts = parts; this.type = opts?.type; } };
        global.URL = { createObjectURL: () => 'blob:url', revokeObjectURL: () => {} };

        class FakeImage {
          constructor(){ this.width = 1; this.height = 1; this.onload = null; }
          set src(v){ if (this.onload) this.onload(); }
        }
        global.Image = FakeImage;

        let rotations = [];
        let cropped = false;
        global.Cropper = class {
          constructor(canvas, opts) {}
          rotate(angle) { rotations.push(angle); }
          getCroppedCanvas() { return { toBlob: (cb) => { cropped = true; cb(new Blob(['a'], { type: 'image/jpeg' })); } }; }
          destroy() {}
        };

        const mainJsPath = %MAIN_JS_PATH%;
        (async () => {
          const mainJsUrl = pathToFileURL(mainJsPath).href;
          await import(mainJsUrl);
          document.dispatchEvent({ type: 'DOMContentLoaded' });

          const file = new File(['dummy'], 'test.jpg', { type: 'image/jpeg' });
          const input = getEl('file-input');
          input.files = [file];
          input.dispatchEvent({ type: 'change', target: { files: [file] } });

          getEl('rotate-left-btn').click();
          getEl('rotate-right-btn').click();
          getEl('save-btn').click();

          assert.deepStrictEqual(rotations, [-90, 90]);
          assert.ok(cropped);
        })();
        """
    )
    js_code = js_code.replace("%MAIN_JS_PATH%", repr(str(main_js)))

    js_file = tmp_path / "main_test.js"
    js_file.write_text(js_code)

    result = subprocess.run(["node", str(js_file)], capture_output=True, text=True)
    assert result.returncode == 0, result.stderr + result.stdout
