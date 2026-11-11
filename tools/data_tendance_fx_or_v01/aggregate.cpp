// Price-data preparation only. No strategy, position, return or performance code.
#include <algorithm>
#include <cstdint>
#include <fstream>
#include <iostream>
#include <map>
#include <sstream>
#include <stdexcept>
#include <string>
#include <vector>
using I = int64_t;
constexpr I SCALE = 1000000000LL;
struct Bar {
    I bo=0,bh=0,bl=0,bc=0,ao=0,ah=0,al=0,ac=0,n=0,first=0,last=0;
    void tick(I t,I b,I a) {
        if(!n) { bo=bh=bl=bc=b; ao=ah=al=ac=a; first=last=t; }
        else {
            bh=std::max(bh,b); bl=std::min(bl,b);
            ah=std::max(ah,a); al=std::min(al,a);
            if(t<first) { first=t; bo=b; ao=a; }
            if(t>=last) { last=t; bc=b; ac=a; }
        }
        ++n;
    }
    void merge(const Bar& b) {
        if(!n) { *this=b; return; }
        bh=std::max(bh,b.bh); bl=std::min(bl,b.bl);
        ah=std::max(ah,b.ah); al=std::min(al,b.al);
        if(b.first<first) { first=b.first; bo=b.bo; ao=b.ao; }
        if(b.last>=last) { last=b.last; bc=b.bc; ac=b.ac; }
        n+=b.n;
    }
};
I digits(const std::string& s,size_t p,size_t n) {
    I v=0;
    if(p+n>s.size()) throw std::runtime_error("short numeric field");
    for(size_t j=p;j<p+n;++j) {
        if(s[j]<'0'||s[j]>'9') throw std::runtime_error("invalid digit");
        v=v*10+s[j]-'0';
    }
    return v;
}
// Howard Hinnant's proleptic Gregorian civil date conversion (Unix epoch).
I civil_days(int y,unsigned m,unsigned d) {
    y-=m<=2; int era=(y>=0?y:y-399)/400;
    unsigned yoe=static_cast<unsigned>(y-era*400);
    unsigned doy=(153*(m+(m>2?-3:9))+2)/5+d-1;
    unsigned doe=yoe*365+yoe/4-yoe/100+doy;
    return era*146097+static_cast<int>(doe)-719468;
}
I price(const std::string& s) {
    size_t p=s.find('.');
    if(p==std::string::npos) return digits(s,0,s.size())*SCALE;
    size_t n=s.size()-p-1;
    if(!p||!n||n>9) throw std::runtime_error("unsupported price precision");
    I tail=digits(s,p+1,n); for(size_t j=n;j<9;++j) tail*=10;
    return digits(s,0,p)*SCALE+tail;
}
std::vector<std::string> split(const std::string& s) {
    std::vector<std::string> r; size_t p=0,q;
    while((q=s.find(',',p))!=std::string::npos) {r.push_back(s.substr(p,q-p));p=q+1;}
    r.push_back(s.substr(p)); return r;
}
std::string decimal(I v) {
    std::string f=std::to_string(v%SCALE+SCALE).substr(1);
    while(f.size()>5&&f.back()=='0') f.pop_back();
    return std::to_string(v/SCALE)+"."+f;
}
int main(int argc,char** argv) {
 try {
    if(argc<2) throw std::runtime_error("mode required");
    std::string mode=argv[1],s;
    std::map<I,Bar> bars;
    if(mode=="ticks") {
        if(argc!=6) throw std::runtime_error("ticks start_ms end_ms dst_intervals stats_json");
        I begin=std::stoll(argv[2]),end=std::stoll(argv[3]);
        std::vector<std::pair<I,I>> dst;
        std::ifstream ds(argv[4]); I a,b;
        while(ds>>a>>b) dst.push_back({a,b});
        if(dst.empty()) throw std::runtime_error("DST intervals missing");
        I rows=0,used=0,backward=0,equal=0,crossed=0,previous=-1,day_key=-1,day_ms=0;
        while(std::getline(std::cin,s)) {
            if(!s.empty()&&s.back()=='\r')s.pop_back();
            if(s.empty()) throw std::runtime_error("blank source row");
            auto f=split(s); if(f.size()!=4||f[0].size()!=18||f[0][8]!=' ')throw std::runtime_error("invalid tick schema at row "+std::to_string(rows+1));
            I dk=digits(f[0],0,8);
            if(dk!=day_key) {
                int y=digits(f[0],0,4),m=digits(f[0],4,2),d=digits(f[0],6,2);
                if(m<1||m>12||d<1||d>31)throw std::runtime_error("bad source date");
                day_ms=civil_days(y,m,d)*86400000LL; day_key=dk;
            }
            I hh=digits(f[0],9,2),mm=digits(f[0],11,2),ss=digits(f[0],13,2),ms=digits(f[0],15,3);
            if(hh>23||mm>59||ss>59)throw std::runtime_error("bad source clock");
            I label=day_ms+hh*3600000+mm*60000+ss*1000+ms;
            I bp=price(f[1]),ap=price(f[2]);
            if(bp<=0||ap<=0)throw std::runtime_error("non-positive quote");
            // Validate the unused source volume as a decimal, never as tick count.
            (void)price(f[3]);
            if(previous>=0) {backward+=label<previous;equal+=label==previous;} previous=label;
            ++rows;crossed+=ap<bp;
            I utc=label+18000000;
            for(auto w:dst) if(utc>=w.first&&utc<w.second){utc-=3600000;break;}
            if(utc<begin||utc>=end)continue;
            ++used; bars[utc/60000].tick(utc,bp,ap);
        }
        std::ofstream st(argv[5]);
        st<<"{\"source_rows\":"<<rows<<",\"included_ticks\":"<<used
          <<",\"source_backward_timestamp_transitions\":"<<backward
          <<",\"source_adjacent_equal_timestamps\":"<<equal
          <<",\"source_crossed_quotes\":"<<crossed<<",\"minute_parts\":"<<bars.size()<<"}\n";
        if(!st)throw std::runtime_error("cannot write stats");
        for(auto& kv:bars){auto v=kv.second;std::cout<<kv.first<<','<<v.bo<<','<<v.bh<<','<<v.bl<<','<<v.bc<<','<<v.ao<<','<<v.ah<<','<<v.al<<','<<v.ac<<','<<v.n<<','<<v.first<<','<<v.last<<'\n';}
    } else if(mode=="merge") {
        while(std::getline(std::cin,s)) {
            auto f=split(s);if(f.size()!=12)throw std::runtime_error("bad partial bar");
            std::vector<I> v;for(auto x:f)v.push_back(std::stoll(x));
            Bar b{v[1],v[2],v[3],v[4],v[5],v[6],v[7],v[8],v[9],v[10],v[11]};
            bars[v[0]].merge(b);
        }
        for(auto& kv:bars){auto v=kv.second;std::cout<<kv.first<<','<<decimal(v.bo)<<','<<decimal(v.bh)<<','<<decimal(v.bl)<<','<<decimal(v.bc)<<','<<decimal(v.ao)<<','<<decimal(v.ah)<<','<<decimal(v.al)<<','<<decimal(v.ac)<<','<<v.n<<'\n';}
    } else throw std::runtime_error("unknown mode");
    if(!std::cout)throw std::runtime_error("output write failed");
    return 0;
 } catch(const std::exception& e){std::cerr<<e.what()<<'\n';return 1;}
}
