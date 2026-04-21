import os
from datetime import date
from flask import Flask, render_template, request, abort
from db import get_stats, get_listings, get_listing, get_price_history, get_sold_listings


# PSEUDOCODE:
# 1. Create Flask app instance
# 2. Apply any config overrides passed in (used by tests)
# 3. Set default DB_PATH to finn_tracker.db in the project root
# 4. Register the format_kr Jinja2 filter
# 5. Register all routes
# 6. Return the app
def create_app(config=None):
    app = Flask(__name__)
    app.config["DB_PATH"] = os.path.join(os.path.dirname(__file__), "finn_tracker.db")

    if config:
        app.config.update(config)

    @app.template_filter("format_kr")
    def format_kr(value):
        # PSEUDOCODE: Format an integer as Norwegian kroner with space as thousands separator
        return "{:,.0f}".format(value).replace(",", " ") + " kr"

    # PSEUDOCODE:
    # 1. Fetch stats for the stats bar (totals, new today, flagged, price-reduced)
    # 2. Fetch all active listings with no filters applied
    # 3. Build sorted list of unique areas for the sidebar dropdown
    # 4. Render index.html with stats, listings, areas, and today's date
    @app.route("/")
    def index():
        stats = get_stats()
        listings = get_listings({})
        omrader = sorted(set(l["omrade"] for l in listings if l["omrade"]))
        return render_template("index.html", stats=stats, listings=listings,
                               omrader=omrader, today_str=str(date.today()))

    # PSEUDOCODE:
    # 1. Parse filter values and sort order from the POST form data
    # 2. Fetch filtered listings from the database
    # 3. Return only the listings partial HTML (for HTMX to swap in)
    @app.route("/annonser", methods=["POST"])
    def annonser():
        filters = {
            "omrade":    request.form.get("omrade") or None,
            "pris_min":  request.form.get("pris_min") or None,
            "pris_maks": request.form.get("pris_maks") or None,
            "bra_min":   request.form.get("bra_min") or None,
            "bra_maks":  request.form.get("bra_maks") or None,
            "rom":       request.form.get("rom") or None,
            "flagg":     request.form.getlist("flagg"),
            "status":    request.form.getlist("status") or None,
        }
        sort = request.form.get("sort", "siste_sett_desc")
        listings = get_listings(filters, sort)
        return render_template("listings.html", listings=listings,
                               today_str=str(date.today()))

    # PSEUDOCODE:
    # 1. Fetch the listing row for the given finnkode
    # 2. If not found, return 404
    # 3. Fetch price history for this listing
    # 4. Render detalj.html with listing and price history
    @app.route("/annonse/<finnkode>")
    def detalj(finnkode):
        listing = get_listing(finnkode)
        if not listing:
            abort(404)
        history = get_price_history(finnkode)
        return render_template("detalj.html", listing=listing, history=history)

    # PSEUDOCODE:
    # 1. Fetch all sold listings
    # 2. Render solgte.html
    @app.route("/solgte")
    def solgte():
        listings = get_sold_listings()
        return render_template("solgte.html", listings=listings)

    # PSEUDOCODE:
    # 1. Fetch all listings flagged as price-reduced
    # 2. Render prishistorikk.html
    @app.route("/prishistorikk")
    def prishistorikk():
        listings = get_listings({"flagg": ["Prisnedsatt"]})
        return render_template("prishistorikk.html", listings=listings)

    @app.errorhandler(404)
    def not_found(e):
        return render_template("404.html"), 404

    return app


if __name__ == "__main__":
    app = create_app()
    app.run(debug=True, port=5000)
