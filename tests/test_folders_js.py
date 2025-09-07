import subprocess
import textwrap
from pathlib import Path


def test_render_tree_js(tmp_path):
    folders_js = (
        Path(__file__).resolve().parent.parent
        / "src" / "web_app" / "static" / "dist" / "folders.js"
    )
    folders_js_str = str(folders_js)
    js_code = textwrap.dedent(
        f"""
        const assert = require('assert');
        const {{ pathToFileURL }} = require('url');

        class Element {{
          constructor(tag = 'div') {{
            this.tag = tag;
            this.children = [];
            this.textContent = '';
            this.firstChild = null;
          }}
          appendChild(child) {{
            this.children.push(child);
            if (!this.firstChild) this.firstChild = child;
            return child;
          }}
        }}

        const document = {{
          createElement: (tag) => new Element(tag)
        }};
        global.document = document;

        const container = new Element('ul');
        const tree = [{{ name: 'A', children: [{{ name: 'B', children: [] }}] }}];

        (async () => {{
          const {{ renderTree }} = await import(pathToFileURL({folders_js_str!r}).href);
          renderTree(container, tree);
          assert.equal(container.children.length, 1);
          const li = container.children[0];
          const details = li.children[0];
          assert.equal(details.children[0].textContent, 'A');
          const ul = details.children[1];
          const childLi = ul.children[0];
          const childDetails = childLi.children[0];
          assert.equal(childDetails.children[0].textContent, 'B');
        }})().catch(err => {{ console.error(err); process.exit(1); }});
        """
    )
    js_file = tmp_path / "folders_test.js"
    js_file.write_text(js_code)
    result = subprocess.run(["node", str(js_file)], capture_output=True, text=True)
    assert result.returncode == 0, result.stderr + result.stdout
