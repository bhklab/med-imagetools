import pandas as pd
from pyvis.network import Network
from pathlib import Path


class TabbedNetwork(Network):
    """
    Subclass PyVis Network to produce an HTML *snippet* (without <html> etc.)
    that we can embed in one larger page with multiple networks.
    """

    def __init__(self, *args, net_id="mynetwork", **kwargs):
        super().__init__(*args, **kwargs)
        self.net_id = net_id  # Unique container ID to avoid collisions

    def generate_html_snippet(self) -> str:
        """
        Returns minimal HTML to embed in a larger document. We:
          - call Network's generate_html()
          - remove top-level <html>/<body> wrappers
          - rename the default "mynetwork" references to self.net_id
        """
        full_html = super().generate_html()  # Full standalone HTML
        # Extract what's inside <body>...</body>
        body_part = full_html.split("<body>", 1)[-1].split("</body>", 1)[0]
        # Rename "mynetwork" references
        snippet = body_part.replace("mynetwork", self.net_id)
        return snippet


def main():
    # -------------------------------------------------------------------------
    # 1) Create some fake DataFrames for demonstration
    # Each will be turned into a separate network
    # -------------------------------------------------------------------------
    df_a = pd.DataFrame({"src": [1, 2, 3], "dst": [2, 3, 4]})
    df_b = pd.DataFrame({"src": [10, 20, 30], "dst": [20, 30, 40]})
    df_c = pd.DataFrame({"src": [100, 101, 102], "dst": [101, 102, 103]})

    # -------------------------------------------------------------------------
    # 2) Build three TabbedNetwork objects
    # -------------------------------------------------------------------------
    netA = TabbedNetwork(
        net_id="netA", height="400px", width="50%", directed=True
    )
    for _, row in df_a.iterrows():
        netA.add_node(int(row["src"]), label=f"A{row['src']}")
        netA.add_node(int(row["dst"]), label=f"A{row['dst']}")
        netA.add_edge(int(row["src"]), int(row["dst"]))

    netB = TabbedNetwork(
        net_id="netB", height="400px", width="50%", directed=True
    )
    for _, row in df_b.iterrows():
        netB.add_node(int(row["src"]), label=f"B{row['src']}")
        netB.add_node(int(row["dst"]), label=f"B{row['dst']}")
        netB.add_edge(int(row["src"]), int(row["dst"]))

    netC = TabbedNetwork(
        net_id="netC", height="400px", width="50%", directed=True
    )
    for _, row in df_c.iterrows():
        netC.add_node(int(row["src"]), label=f"C{row['src']}")
        netC.add_node(int(row["dst"]), label=f"C{row['dst']}")
        netC.add_edge(int(row["src"]), int(row["dst"]))

    # -------------------------------------------------------------------------
    # 3) Generate HTML snippets from each
    # -------------------------------------------------------------------------
    snippetA = netA.generate_html_snippet()
    snippetB = netB.generate_html_snippet()
    snippetC = netC.generate_html_snippet()

    # -------------------------------------------------------------------------
    # 4) Create one final HTML doc with tabs
    #    Each "tab" simply toggles display of the div that contains a snippet
    # -------------------------------------------------------------------------
    final_html = f"""
    <!DOCTYPE html>
    <html>
    <head>
      <meta charset="UTF-8"/>
      <title>Tabbed PyVis Demo</title>
      <script
        src="https://cdn.jsdelivr.net/npm/vis-network@9.1.2/standalone/umd/vis-network.min.js"
        integrity="sha512-+nq6q1Czox9NpjF1Ek3IS7oBMNfPb1EYxlqzoNi1CW6QzjWv6+u32gjygEH5AyQpEMLNvMo5d4r8bYC/bEXmYA=="
        crossorigin="anonymous"
      ></script>
      <style>
        .tabButton {{
          background-color: #eee; 
          margin: 4px; 
          padding: 4px 8px; 
          border: 1px solid #aaa;
          cursor: pointer;
        }}
        .tabButton:hover {{
          background-color: #ccc;
        }}
        .tabContent {{
          display: none;
        }}
      </style>
    </head>
    <body>
      <h2>Tabbed PyVis Networks</h2>
      <div>
        <span class="tabButton" onclick="showTab('tabA')">Network A</span>
        <span class="tabButton" onclick="showTab('tabB')">Network B</span>
        <span class="tabButton" onclick="showTab('tabC')">Network C</span>
      </div>

      <!-- Container for each network snippet -->
      <div id="tabA" class="tabContent">
        {snippetA}
      </div>
      <div id="tabB" class="tabContent">
        {snippetB}
      </div>
      <div id="tabC" class="tabContent">
        {snippetC}
      </div>

      <script>
        function showTab(tabId) {{
          document.getElementById("tabA").style.display = "none";
          document.getElementById("tabB").style.display = "none";
          document.getElementById("tabC").style.display = "none";
          document.getElementById(tabId).style.display = "block";
        }}
        // Auto-show the first tab
        showTab("tabA");
      </script>
    </body>
    </html>
    """

    # -------------------------------------------------------------------------
    # 5) Write final HTML, then open in a browser
    # -------------------------------------------------------------------------
    out_file = Path("tabbed_networks.html")
    out_file.write_text(final_html, encoding="utf-8")
    print(f"Done. Open {out_file.absolute()} in your browser.")


if __name__ == "__main__":
    main()
