from textwrap import dedent

import numpy as np
import pytest

from pandas import (
    DataFrame,
    MultiIndex,
    option_context,
)

jinja2 = pytest.importorskip("jinja2")
from pandas.io.formats.style import Styler

loader = jinja2.PackageLoader("pandas", "io/formats/templates")
env = jinja2.Environment(loader=loader, trim_blocks=True)


@pytest.fixture
def styler():
    return Styler(DataFrame([[2.61], [2.69]], index=["a", "b"], columns=["A"]))


@pytest.fixture
def styler_mi():
    midx = MultiIndex.from_product([["a", "b"], ["c", "d"]])
    return Styler(DataFrame(np.arange(16).reshape(4, 4), index=midx, columns=midx))


@pytest.fixture
def tpl_style():
    return env.get_template("html_style.tpl")


@pytest.fixture
def tpl_table():
    return env.get_template("html_table.tpl")


def test_html_template_extends_options():
    # make sure if templates are edited tests are updated as are setup fixtures
    # to understand the dependency
    with open("pandas/io/formats/templates/html.tpl") as file:
        result = file.read()
    assert "{% include html_style_tpl %}" in result
    assert "{% include html_table_tpl %}" in result


def test_exclude_styles(styler):
    result = styler.to_html(exclude_styles=True, doctype_html=True)
    expected = dedent(
        """\
        <!DOCTYPE html>
        <html>
        <head>
        <meta charset="utf-8">
        </head>
        <body>
        <table>
          <thead>
            <tr>
              <th >&nbsp;</th>
              <th >A</th>
            </tr>
          </thead>
          <tbody>
            <tr>
              <th >a</th>
              <td >2.610000</td>
            </tr>
            <tr>
              <th >b</th>
              <td >2.690000</td>
            </tr>
          </tbody>
        </table>
        </body>
        </html>
        """
    )
    assert result == expected


def test_w3_html_format(styler):
    styler.set_uuid("").set_table_styles(
        [{"selector": "th", "props": "att2:v2;"}]
    ).applymap(lambda x: "att1:v1;").set_table_attributes(
        'class="my-cls1" style="attr3:v3;"'
    ).set_td_classes(
        DataFrame(["my-cls2"], index=["a"], columns=["A"])
    ).format(
        "{:.1f}"
    ).set_caption(
        "A comprehensive test"
    )
    expected = dedent(
        """\
        <style type="text/css">
        #T_ th {
          att2: v2;
        }
        #T_row0_col0, #T_row1_col0 {
          att1: v1;
        }
        </style>
        <table id="T_" class="my-cls1" style="attr3:v3;">
          <caption>A comprehensive test</caption>
          <thead>
            <tr>
              <th class="blank level0" >&nbsp;</th>
              <th class="col_heading level0 col0" >A</th>
            </tr>
          </thead>
          <tbody>
            <tr>
              <th id="T_level0_row0" class="row_heading level0 row0" >a</th>
              <td id="T_row0_col0" class="data row0 col0 my-cls2" >2.6</td>
            </tr>
            <tr>
              <th id="T_level0_row1" class="row_heading level0 row1" >b</th>
              <td id="T_row1_col0" class="data row1 col0" >2.7</td>
            </tr>
          </tbody>
        </table>
        """
    )
    assert expected == styler.render()


def test_colspan_w3():
    # GH 36223
    df = DataFrame(data=[[1, 2]], columns=[["l0", "l0"], ["l1a", "l1b"]])
    styler = Styler(df, uuid="_", cell_ids=False)
    assert '<th class="col_heading level0 col0" colspan="2">l0</th>' in styler.render()


def test_rowspan_w3():
    # GH 38533
    df = DataFrame(data=[[1, 2]], index=[["l0", "l0"], ["l1a", "l1b"]])
    styler = Styler(df, uuid="_", cell_ids=False)
    assert (
        '<th id="T___level0_row0" class="row_heading '
        'level0 row0" rowspan="2">l0</th>' in styler.render()
    )


def test_styles(styler):
    styler.set_uuid("abc_")
    styler.set_table_styles([{"selector": "td", "props": "color: red;"}])
    result = styler.to_html(doctype_html=True)
    expected = dedent(
        """\
        <!DOCTYPE html>
        <html>
        <head>
        <meta charset="utf-8">
        <style type="text/css">
        #T_abc_ td {
          color: red;
        }
        </style>
        </head>
        <body>
        <table id="T_abc_">
          <thead>
            <tr>
              <th class="blank level0" >&nbsp;</th>
              <th class="col_heading level0 col0" >A</th>
            </tr>
          </thead>
          <tbody>
            <tr>
              <th id="T_abc_level0_row0" class="row_heading level0 row0" >a</th>
              <td id="T_abc_row0_col0" class="data row0 col0" >2.610000</td>
            </tr>
            <tr>
              <th id="T_abc_level0_row1" class="row_heading level0 row1" >b</th>
              <td id="T_abc_row1_col0" class="data row1 col0" >2.690000</td>
            </tr>
          </tbody>
        </table>
        </body>
        </html>
        """
    )
    assert result == expected


def test_doctype(styler):
    result = styler.to_html(doctype_html=False)
    assert "<html>" not in result
    assert "<body>" not in result
    assert "<!DOCTYPE html>" not in result
    assert "<head>" not in result


def test_block_names(tpl_style, tpl_table):
    # catch accidental removal of a block
    expected_style = {
        "before_style",
        "style",
        "table_styles",
        "before_cellstyle",
        "cellstyle",
    }
    expected_table = {
        "before_table",
        "table",
        "caption",
        "thead",
        "tbody",
        "after_table",
        "before_head_rows",
        "head_tr",
        "after_head_rows",
        "before_rows",
        "tr",
        "after_rows",
    }
    result1 = set(tpl_style.blocks)
    assert result1 == expected_style

    result2 = set(tpl_table.blocks)
    assert result2 == expected_table


def test_from_custom_template_table(tmpdir):
    p = tmpdir.mkdir("tpl").join("myhtml_table.tpl")
    p.write(
        dedent(
            """\
            {% extends "html_table.tpl" %}
            {% block table %}
            <h1>{{custom_title}}</h1>
            {{ super() }}
            {% endblock table %}"""
        )
    )
    result = Styler.from_custom_template(str(tmpdir.join("tpl")), "myhtml_table.tpl")
    assert issubclass(result, Styler)
    assert result.env is not Styler.env
    assert result.template_html_table is not Styler.template_html_table
    styler = result(DataFrame({"A": [1, 2]}))
    assert "<h1>My Title</h1>\n\n\n<table" in styler.render(custom_title="My Title")


def test_from_custom_template_style(tmpdir):
    p = tmpdir.mkdir("tpl").join("myhtml_style.tpl")
    p.write(
        dedent(
            """\
            {% extends "html_style.tpl" %}
            {% block style %}
            <link rel="stylesheet" href="mystyle.css">
            {{ super() }}
            {% endblock style %}"""
        )
    )
    result = Styler.from_custom_template(
        str(tmpdir.join("tpl")), html_style="myhtml_style.tpl"
    )
    assert issubclass(result, Styler)
    assert result.env is not Styler.env
    assert result.template_html_style is not Styler.template_html_style
    styler = result(DataFrame({"A": [1, 2]}))
    assert '<link rel="stylesheet" href="mystyle.css">\n\n<style' in styler.render()


def test_caption_as_sequence(styler):
    styler.set_caption(("full cap", "short cap"))
    assert "<caption>full cap</caption>" in styler.render()


@pytest.mark.parametrize("index", [False, True])
@pytest.mark.parametrize("columns", [False, True])
@pytest.mark.parametrize("index_name", [True, False])
def test_sticky_basic(styler, index, columns, index_name):
    if index_name:
        styler.index.name = "some text"
    if index:
        styler.set_sticky(axis=0)
    if columns:
        styler.set_sticky(axis=1)

    res = styler.set_uuid("").to_html()

    css_for_index = (
        "tr th:first-child {\n  position: sticky;\n  background-color: white;\n  "
        "left: 0px;\n  z-index: 1;\n}"
    )
    assert (css_for_index in res) is index

    css_for_cols_1 = (
        "thead tr:first-child {\n  position: sticky;\n  background-color: white;\n  "
        "top: 0px;\n  z-index: 2;\n"
    )
    css_for_cols_1 += "  height: 25px;\n}" if index_name else "}"
    assert (css_for_cols_1 in res) is columns

    css_for_cols_2 = (
        "thead tr:nth-child(2) {\n  position: sticky;\n  background-color: white;\n  "
        "top: 25px;\n  z-index: 2;\n  height: 25px;\n}"
    )
    assert (css_for_cols_2 in res) is (index_name and columns)


@pytest.mark.parametrize("index", [False, True])
@pytest.mark.parametrize("columns", [False, True])
def test_sticky_mi(styler_mi, index, columns):
    if index:
        styler_mi.set_sticky(axis=0)
    if columns:
        styler_mi.set_sticky(axis=1)

    res = styler_mi.set_uuid("").to_html()
    assert (
        (
            dedent(
                """\
        #T_ tbody th.level0 {
          position: sticky;
          left: 0px;
          min-width: 75px;
          max-width: 75px;
          background-color: white;
        }
        """
            )
            in res
        )
        is index
    )
    assert (
        (
            dedent(
                """\
        #T_ tbody th.level1 {
          position: sticky;
          left: 75px;
          min-width: 75px;
          max-width: 75px;
          background-color: white;
        }
        """
            )
            in res
        )
        is index
    )
    assert (
        (
            dedent(
                """\
        #T_ thead th.level0 {
          position: sticky;
          top: 0px;
          height: 25px;
          background-color: white;
        }
        """
            )
            in res
        )
        is columns
    )
    assert (
        (
            dedent(
                """\
        #T_ thead th.level1 {
          position: sticky;
          top: 25px;
          height: 25px;
          background-color: white;
        }
        """
            )
            in res
        )
        is columns
    )


@pytest.mark.parametrize("index", [False, True])
@pytest.mark.parametrize("columns", [False, True])
def test_sticky_levels(styler_mi, index, columns):
    if index:
        styler_mi.set_sticky(axis=0, levels=[1])
    if columns:
        styler_mi.set_sticky(axis=1, levels=[1])

    res = styler_mi.set_uuid("").to_html()
    assert "#T_ tbody th.level0 {" not in res
    assert "#T_ thead th.level0 {" not in res
    assert (
        (
            dedent(
                """\
        #T_ tbody th.level1 {
          position: sticky;
          left: 0px;
          min-width: 75px;
          max-width: 75px;
          background-color: white;
        }
        """
            )
            in res
        )
        is index
    )
    assert (
        (
            dedent(
                """\
        #T_ thead th.level1 {
          position: sticky;
          top: 0px;
          height: 25px;
          background-color: white;
        }
        """
            )
            in res
        )
        is columns
    )


def test_sticky_raises(styler):
    with pytest.raises(ValueError, match="`axis` must be"):
        styler.set_sticky(axis="bad")


@pytest.mark.parametrize(
    "sparse_index, sparse_columns",
    [(True, True), (True, False), (False, True), (False, False)],
)
def test_sparse_options(sparse_index, sparse_columns):
    cidx = MultiIndex.from_tuples([("Z", "a"), ("Z", "b"), ("Y", "c")])
    ridx = MultiIndex.from_tuples([("A", "a"), ("A", "b"), ("B", "c")])
    df = DataFrame([[1, 2, 3], [4, 5, 6], [7, 8, 9]], index=ridx, columns=cidx)
    styler = df.style

    default_html = styler.to_html()  # defaults under pd.options to (True , True)

    with option_context(
        "styler.sparse.index", sparse_index, "styler.sparse.columns", sparse_columns
    ):
        html1 = styler.to_html()
        assert (html1 == default_html) is (sparse_index and sparse_columns)
    html2 = styler.to_html(sparse_index=sparse_index, sparse_columns=sparse_columns)
    assert html1 == html2
