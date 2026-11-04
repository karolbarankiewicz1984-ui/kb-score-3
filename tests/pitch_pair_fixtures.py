"""Independent synthetic stats, with explicit expected counts (no inference)."""
def stats(mid,home,away,h,a,nh=1,na=1):
    return {"data":{"match_id":mid,"home_team":{"id":home},"away_team":{"id":away},
        "periods":[{"period":"All","groups":[
            {"group_name":"Expected goals (xG)","items":[
                {"key":"expected_goals","format_type":"double","home":str(h),"away":str(a)}]},
            {"group_name":"Shots","items":[
                {"key":"total_shots","format_type":"integer","home":str(nh),"away":str(na)}]}
        ]}]}}
