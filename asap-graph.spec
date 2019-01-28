Name:		asap-graph		
Version:	1.0.3
Release:	1%{?dist}
Summary:	sar graphing tool

License:	MIT
URL:            https://github.com/Rezney/asap-graph		
Source0:	asap-graph-1.0.3.tar.gz

Requires:	python3-docopt python3-matplotlib	

%description

asap-graph is a sar graphing tool using matplotlib capable of plotting 
a single file, an interval of files, or go recursively through a folder, 
i.e. sosreport folder. 

%prep
%setup -q
mkdir -p %{buildroot}%{_usr}/share/asap-graph
mkdir -p %{buildroot}%{_bindir}
cp mystyle.mplstyle %{buildroot}%{_usr}/share/asap-graph/mystyle.mplstyle
cp asap-graph %{buildroot}%{_bindir}/asap-graph


%files
%{_usr}/share/asap-graph/mystyle.mplstyle
%{_bindir}/asap-graph
%attr(0755, root, root) %{_bindir}/asap-graph


%changelog

* Thu Nov 29 2018 George Angelopoulos
- fix ldavg labels and variable names 
