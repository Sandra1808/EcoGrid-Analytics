package EcoGrid.entity;

import jakarta.persistence.*;
import jakarta.validation.constraints.NotNull;
import org.hibernate.annotations.OnDelete;
import org.hibernate.annotations.OnDeleteAction;

import java.math.BigDecimal;

@Entity
@Table(name = "DEMANDAGENERACIONREE")
public class Demandageneracionree {
    @Id
    @GeneratedValue(strategy = GenerationType.IDENTITY)
    @Column(name = "IDDEMANDA", nullable = false)
    private Long id;

    @NotNull
    @ManyToOne(fetch = FetchType.LAZY, optional = false)
    @OnDelete(action = OnDeleteAction.RESTRICT)
    @JoinColumn(name = "IDTIEMPO", nullable = false)
    private Tiempohorario idtiempo;

    @NotNull
    @ManyToOne(fetch = FetchType.LAZY, optional = false)
    @OnDelete(action = OnDeleteAction.RESTRICT)
    @JoinColumn(name = "IDCCAA", nullable = false)
    private Comunidadautonoma idccaa;

    @Column(name = "DEMANDAREALMW", precision = 12, scale = 4)
    private BigDecimal demandarealmw;

    @Column(name = "DEMANDAPREVISTAREEMW", precision = 12, scale = 4)
    private BigDecimal demandaprevistareemw;

    @Column(name = "DEMANDAPROGRAMADAMW", precision = 12, scale = 4)
    private BigDecimal demandaprogramadamw;

    @Column(name = "DEMANDAPROGRAMADATOTALMW", precision = 12, scale = 4)
    private BigDecimal demandaprogramadatotalmw;

    @Column(name = "GENEOLICAMW", precision = 12, scale = 4)
    private BigDecimal geneolicamw;

    @Column(name = "GENSOLARMW", precision = 12, scale = 4)
    private BigDecimal gensolarmw;

    @Column(name = "GENHIDRAULICAMW", precision = 12, scale = 4)
    private BigDecimal genhidraulicamw;

    @Column(name = "GENNUCLEARMW", precision = 12, scale = 4)
    private BigDecimal gennuclearmw;

    @Column(name = "GENCICLOCOMBINADOMW", precision = 12, scale = 4)
    private BigDecimal genciclocombinadomw;

    public Long getId() {
        return id;
    }

    public void setId(Long id) {
        this.id = id;
    }

    public Tiempohorario getIdtiempo() {
        return idtiempo;
    }

    public void setIdtiempo(Tiempohorario idtiempo) {
        this.idtiempo = idtiempo;
    }

    public Comunidadautonoma getIdccaa() {
        return idccaa;
    }

    public void setIdccaa(Comunidadautonoma idccaa) {
        this.idccaa = idccaa;
    }

    public BigDecimal getDemandarealmw() {
        return demandarealmw;
    }

    public void setDemandarealmw(BigDecimal demandarealmw) {
        this.demandarealmw = demandarealmw;
    }

    public BigDecimal getDemandaprevistareemw() {
        return demandaprevistareemw;
    }

    public void setDemandaprevistareemw(BigDecimal demandaprevistareemw) {
        this.demandaprevistareemw = demandaprevistareemw;
    }

    public BigDecimal getDemandaprogramadamw() {
        return demandaprogramadamw;
    }

    public void setDemandaprogramadamw(BigDecimal demandaprogramadamw) {
        this.demandaprogramadamw = demandaprogramadamw;
    }

    public BigDecimal getDemandaprogramadatotalmw() {
        return demandaprogramadatotalmw;
    }

    public void setDemandaprogramadatotalmw(BigDecimal demandaprogramadatotalmw) {
        this.demandaprogramadatotalmw = demandaprogramadatotalmw;
    }

    public BigDecimal getGeneolicamw() {
        return geneolicamw;
    }

    public void setGeneolicamw(BigDecimal geneolicamw) {
        this.geneolicamw = geneolicamw;
    }

    public BigDecimal getGensolarmw() {
        return gensolarmw;
    }

    public void setGensolarmw(BigDecimal gensolarmw) {
        this.gensolarmw = gensolarmw;
    }

    public BigDecimal getGenhidraulicamw() {
        return genhidraulicamw;
    }

    public void setGenhidraulicamw(BigDecimal genhidraulicamw) {
        this.genhidraulicamw = genhidraulicamw;
    }

    public BigDecimal getGennuclearmw() {
        return gennuclearmw;
    }

    public void setGennuclearmw(BigDecimal gennuclearmw) {
        this.gennuclearmw = gennuclearmw;
    }

    public BigDecimal getGenciclocombinadomw() {
        return genciclocombinadomw;
    }

    public void setGenciclocombinadomw(BigDecimal genciclocombinadomw) {
        this.genciclocombinadomw = genciclocombinadomw;
    }

}