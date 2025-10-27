# TESTINFO.md

This document summarizes the **49 automated tests** for the `Flask_app.py` and `sqlQueries.py` modules.  
Tests are grouped by subsystem.

---

## Helpers

**test_money_and_cents_helpers**  
- Passed: `_money(1.235)`, `_money("x")`, `_cents_to_dollars(250)`, `_cents_to_dollars(None)`  
- Expected: Rounded 1.23→1.24, 0.0 for bad input, 2.5, 0.0  
- Tests rounding and safe casting.

**test_money_rounding_and_negatives**  
- Passed: `_money(1.005)`, `_money(-3.333)`, `_money("nope")`  
- Expected: 1.00/1.01, -3.33, 0.0  
- Tests rounding edge cases and error handling.

**test_cents_to_dollars_varied_inputs**  
- Passed: 250, -125, None  
- Expected: 2.5, -1.25, 0.0  
- Tests positive/negative/None conversions.

**test_parse_generated_menu_basic**  
- Passed: "[2025-10-27,5,1][2025-10-27,6]"  
- Expected: Two entries; meal=1 and default=3  
- Tests parsing format and legacy default meal.

**test_parse_generated_menu_empty**  
- Passed: ""  
- Expected: {}  
- Tests empty string input.

**test_parse_generated_menu_ignores_bad_tokens**  
- Passed: string with junk and valid tokens  
- Expected: Keeps valid dates, ignores bad ones  
- Tests robustness.

**test_parse_generated_menu_spaces_and_legacy**  
- Passed: "[ 2025-10-27 , 5 ] [2025-10-27,6,1]"  
- Expected: Two entries; meals [1,3]  
- Tests whitespace + legacy default.

**test_palette_deterministic**  
- Passed: ids [1,2,1]  
- Expected: Same id → same color, different → different  
- Tests color consistency.

**test_palette_for_item_ids_empty**  
- Passed: []  
- Expected: {}  
- Tests empty input.

**test_build_calendar_cells_empty_month_structure**  
- Passed: gen_map={}, items_by_id={}  
- Expected: Grid matches calendar weeks, blanks=day=0  
- Tests calendar grid shape.

**test_build_calendar_cells_meal_sort_order**  
- Passed: gen_map with meal 1 & 3 on same day  
- Expected: Sorted [1,3]  
- Tests breakfast→lunch→dinner sort.

**test_fetch_menu_items_by_ids**  
- Passed: Valid ids  
- Expected: Dict with item info & restaurant_name  
- Tests DB join retrieval.

**test_fetch_menu_items_by_ids_empty_returns_empty**  
- Passed: []  
- Expected: {}  
- Tests empty input guard.

---

## Authentication & Session

**test_modules_import**  
- Passed: "Flask_app", "sqlQueries"  
- Expected: Import succeeds  
- Tests module import.

**test_flask_app_exposes_app_if_present**  
- Passed: Flask_app.app  
- Expected: Flask instance  
- Tests app exposure.

**test_root_route_smoke**  
- Passed: GET "/"  
- Expected: Status 200/302/404  
- Basic availability check.

**test_login_get_ok**  
- Passed: GET "/login"  
- Expected: 200, template rendered  
- Tests login page.

**test_login_post_success_and_fail**  
- Passed: Good & bad creds  
- Expected: 200/3xx on success, error on fail  
- Tests login behavior.

**test_logout_clears_session**  
- Passed: GET "/logout" then "/"  
- Expected: Redirect to login  
- Tests session clearing.

---

## Registration

**test_register_get_200**  
- Passed: GET "/register"  
- Expected: 200, template rendered  
- Tests register page.

**test_register_post_invalid_email**  
- Passed: bad email  
- Expected: Error template  
- Tests email validation.

**test_register_post_mismatch_password**  
- Passed: mismatch passwords  
- Expected: Error  
- Tests confirm password.

**test_register_post_short_password**  
- Passed: short password  
- Expected: Error  
- Tests min length.

**test_register_post_bad_phone**  
- Passed: too short phone  
- Expected: Error  
- Tests phone validation.

**test_register_post_success_and_duplicate**  
- Passed: good registration, then duplicate  
- Expected: Redirect, then error  
- Tests duplicate prevention.

---

## Profile & Password

**test_index_requires_login_then_ok**  
- Passed: GET "/" pre/post login  
- Expected: Redirect before, success after  
- Tests index guard.

**test_profile_lists_orders_and_wallet**  
- Passed: GET "/profile" after login  
- Expected: Orders listed, wallet in dollars  
- Tests profile data.

**test_profile_requires_login_redirect**  
- Passed: GET "/profile" unauthenticated  
- Expected: Redirect  
- Tests guard.

**test_profile_edit_get_and_post**  
- Passed: GET + POST updates  
- Expected: 200 then redirect  
- Tests editing profile.

**test_change_password_flow**  
- Passed: valid current/new  
- Expected: Success redirect  
- Tests happy path.

**test_change_password_missing_current**  
- Passed: missing current_password  
- Expected: Redirect with pw_error  
- Tests error.

**test_change_password_same_as_current**  
- Passed: same new/current  
- Expected: Redirect with pw_error  
- Tests blocked reuse.

**test_change_password_incorrect_current**  
- Passed: wrong current password  
- Expected: Redirect with pw_error  
- Tests validation.

---

## Orders

**test_orders_route_lists_restaurants_and_items**  
- Passed: GET "/orders" logged in  
- Expected: Orders template  
- Tests page render.

**test_orders_page_lists_only_instock**  
- Passed: GET "/orders"  
- Expected: Lists only in-stock items  
- Tests SQL filter.

**test_orders_json_missing_items_400**  
- Passed: {"restaurant_id":1, items:[]}  
- Expected: 400 error  
- Tests missing items.

**test_orders_json_invalid_restaurant_400**  
- Passed: restaurant_id=0  
- Expected: 400  
- Tests invalid id.

**test_orders_json_mixed_restaurants_400**  
- Passed: items from diff restaurants  
- Expected: 400 {"error":"mixed_restaurants"}  
- Tests enforcement of single-restaurant.

**test_orders_json_success_with_weird_delivery_type**  
- Passed: delivery_type="WEIRD"  
- Expected: Success normalized to delivery  
- Tests robustness.

**test_order_post_json_group_success**  
- Passed: valid group order JSON  
- Expected: {"ok":True,"ord_id":int}  
- Tests happy path.

**test_order_legacy_missing_item_redirects**  
- Passed: GET "/order" no itm_id  
- Expected: Redirect  
- Tests legacy path.

**test_order_legacy_bad_item_redirects**  
- Passed: itm_id=999999  
- Expected: Redirect  
- Tests invalid item.

**test_order_receipt_pdf_endpoint** (skipped if lib missing)  
- Passed: GET receipt.pdf  
- Expected: PDF bytes  
- Tests PDF generation.

---

## Database Viewer

**test_db_view_pagination**  
- Passed: /db?t=User&page=1  
- Expected: Template or login redirect  
- Tests pagination.

**test_db_view_invalid_table_falls_back**  
- Passed: /db?t=Nope  
- Expected: Fallback template  
- Tests allowed table guard.

**test_db_view_out_of_range_page_clamps**  
- Passed: /db?t=User&page=9999  
- Expected: Clamped page render  
- Tests pagination edge.

---

## SQL Queries Module

**test_sql_create_and_close**  
- Passed: create_connection, close_connection  
- Expected: Works without error  
- Tests connection lifecycle.

**test_sql_execute_and_fetch**  
- Passed: insert + fetch  
- Expected: Row retrieved  
- Tests execute/fetch correctness.

---

# Summary

- **Helpers:** 13 tests  
- **Auth & Session:** 6 tests  
- **Registration:** 6 tests  
- **Profile & Password:** 8 tests  
- **Orders:** 11 tests (+1 optional PDF)  
- **DB Viewer:** 3 tests  
- **SQL Queries:** 2 tests  

**Total: 49 tests (48 regular + 1 optional PDF).**

